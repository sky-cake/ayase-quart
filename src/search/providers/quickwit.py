from itertools import batched
from typing import Any

from orjson import dumps, loads

from . import (
    MAX_RESULTS_LIMIT,
    POST_PK,
    SearchIndexField,
    SearchQuery,
    search_index_fields
)
from .baseprovider import BaseSearch, get_doc_pks

pk = POST_PK


class QuickwitSearch(BaseSearch):
    version: str

    def __init__(self, host: str, config: dict=None, **kwargs):
        super().__init__(host, config, **kwargs)
        self.version = config['version']

    def _get_index_url(self, index: str):
        return f'{self.host}/api/v1/indexes/{index}'

    def _get_index_url2(self, index: str):
        return f'{self.host}/api/v1/{index}'

    async def _create_index(self, index: str):
        url = self.host + '/api/v1/indexes'
        payload = {
            'version': self.version,
            'index_id': index,
            'doc_mapping': {
                # https://quickwit.io/docs/configuration/index-config#doc-mapping
                'field_mappings': [_get_qw_field(f) for f in search_index_fields],
                'timestamp_field': 'timestamp',
                'index_field_presence': True,
            },
            'search_settings': {
                'default_search_fields': ['comment', 'title']
            },
            'indexing_settings': {
                'commit_timeout_secs': 30,
            },
        }
        resp = await self.client.post(url, data=dumps(payload))
        return loads(await resp.read())

    async def _index_clear(self, index: str):
        url = self._get_index_url(index) + '/clear'
        resp = await self.client.delete(url)
        return loads(await resp.read())

    async def _index_delete(self, index: str):
        url = self._get_index_url(index)
        resp = await self.client.delete(url)
        return loads(await resp.read())

    async def _index_ready(self, index: str):
        return True

    async def _index_stats(self, index: str):
        url = self._get_index_url(index) + '/describe'
        resp = await self.client.get(url)
        return loads(await resp.read())

    async def _add_docs(self, index: str, docs: list[Any]):
        # await self._remove_docs(index, get_doc_pks(docs))
        url = self._get_index_url2(index) + '/ingest'
        # this 10k limit is documented nowhere...
        for batch in batched(docs, 10000):
            data = b'\n'.join(dumps(doc) for doc in batch)
            params = {'commit': 'force'}
            resp = await self.client.post(url, data=data, params=params)
            # print(loads(await resp.read()))
        return None

    async def _remove_docs(self, index: str, pk_ids: list[str]):
        # There are bugs with the delete api
        # https://github.com/quickwit-oss/quickwit/issues/3762
        # https://github.com/quickwit-oss/quickwit/issues/3612
        if not pk_ids: return
        url = self._get_index_url2(index) + '/delete-tasks'
        payload = {
            "query": f"pk IN [{' '.join(pk_ids)}]",
            "search_fields": ['pk'],
        }
        resp = await self.client.post(url, data=dumps(payload))
        print(loads(await resp.read()))
        return None

    async def _search_index(self, index: str, q: SearchQuery):
        url = self._get_index_url2(index) + '/search'
        params = {
            'max_hits': q.result_limit,
            'sort_by': ('-' if q.sort == 'asc' else '+') + 'timestamp',
            'format': 'json',
            'start_offset': 0 if q.page <= 1 else q.page * q.result_limit,
            'query': get_qw_query(q),
        }
        print(get_qw_query(q))
        if q.after is not None:
            params['start_timestamp'] = q.after
        if q.before is not None:
            params['end_timestamp'] = q.before
        resp = await self.client.get(url, params=params)
        data = loads(await resp.read())
        if not 'hits' in data:
            print(data)
            return [], 0
        total = data['num_hits']
        hits = [_restore_result(res) for res in data['hits']]
        return hits, total

def get_qw_query(q: SearchQuery):
    qb = []
    if q.comment:
        comment = esc_term(q.comment)
        qb.append(f'comment:{comment}')
    if q.title:
        title = esc_term(q.title)
        qb.append(f'comment:{title}')
    if q.boards is not None:
        qb.append(f'board:IN [{" ".join(q.boards)}]')
    if q.num is not None:
        qb.append(f'num:{q.num}')
    if q.media_file is not None:
        qb.append(f'media_file:{q.media_file}')
    if q.media_hash is not None:
        qb.append(f'media_hash:{q.media_hash}')
    if q.deleted is not None:
        qb.append(f'deleted:{str(q.deleted).lower()}')
    if q.op is not None:
        qb.append(f'op:{str(q.op).lower()}')
    if q.has_file is not None or q.has_no_file is not None:
        if q.has_file or (not q.has_no_file):
            qb.append(f'(media_hash:* OR media_file:*)')
        else:
            qb.append(f'-(media_hash:* AND media_file:*)')
    return ' AND '.join(qb)

def _get_field_type(field: SearchIndexField):
    if field.field == 'timestamp':
        return 'datetime'
    if field.field_type is str:
        return 'text'
    if field.field_type is bool:
        return 'bool'
    if field.field_type is int:
        return 'u64'
    if field.field_type is float:
        return 'f64'


def _get_qw_field(field: SearchIndexField):
    qw_field = {
        'name': field.field,
        'type': _get_field_type(field),
    }
    if (field.searchable or field.field == 'pk') and field.field_type is str:
        qw_field['indexed'] = True
        qw_field['tokenizer'] = 'default'
        qw_field['fast'] = False
        qw_field['record'] = 'basic'
    if field.field_type is int or field.sortable or field.filterable:
        qw_field['fast'] = True
    if field.field == 'timestamp':
        qw_field['input_formats'] = ['unix_timestamp']
        qw_field['output_format'] = 'unix_timestamp_secs'
        qw_field['fast_precision'] = 'seconds'
    return qw_field


def _restore_result(res: dict):
    return {'comment': res.get('comment'), **loads(res['data'])}

chars = '+ ^ ` : { } " [ ] ( ) ~ ! \\ *'.split()
def esc_term(term: str):
    for c in chars:
        term = term.replace(c, r'\\' + c)
    return term