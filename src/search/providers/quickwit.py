from orjson import dumps, loads

from . import (
    MAX_RESULTS,
    POST_PK,
    SearchIndexField,
    SearchQuery,
    search_index_fields
)
from .baseprovider import BaseSearch

pk = POST_PK


class QuickwitSearch(BaseSearch):
    version: str

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.version = kwargs['config']['version']

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
                'field_mapping': [_get_qw_field(f) for f in search_index_fields],
            },
            'search_settings': {'default_search_fields': ['comment', 'title']},
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

    async def _add_docs(self, index: str, docs: list[any]):
        url = self._get_index_url(index) + '/ingest'
        data = b'\n'.join(dumps(doc) for doc in docs)
        resp = await self.client.post(url, data=data)
        return loads(await resp.read())

    async def _remove_docs(self, index: str, pk_ids: list[str]):
        if not pk_ids:
            return
        url = self._get_index_url2(index) + '/delete-tasks'
        payload = {
            "query": f"pk IN [{' '.join(pk_ids)}]",
            "search_field": ['pk'],
        }
        resp = await self.client.delete(url, data=dumps(payload))
        return loads(await resp.read())

    async def _search_index(self, index: str, q: SearchQuery):
        url = self._get_index_url2(index) + '/search'
        params = {
            'max_hits': q.result_limit,
            'sort_by': 'timestamp',
            'format': 'json',
            'start_offset': 0 if q.page <= 1 else q.page * q.result_limit,
        }
        if q.after is not None:
            params['start_timestame'] = q.after
        if q.before is not None:
            params['end_timestame'] = q.before
        resp = await self.client.get(url, params=params)
        data = loads(await resp.read())
        if not 'hits' in data:
            print(data)
            return [], 0
        total = data['num_hits']
        hits = [_restore_result(res) for res in data['hits']]
        return hits, total


def _get_field_type(field: SearchIndexField):
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
        'type': _get_field_type(field),
    }

    return qw_field


def _restore_result(res: dict):
    return {'comment': res['comment'], **loads(res['data'])}
