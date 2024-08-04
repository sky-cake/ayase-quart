from orjson import dumps, loads

from . import (
    MAX_RESULTS,
    POST_PK,
    SearchIndexField,
    SearchQuery,
    search_index_fields
)
from .baseprovider import BaseSearch, get_doc_pks

pk = POST_PK


class LnxSearch(BaseSearch):
    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

    def _get_index_url(self, index: str):
        return f'{self.host}/indexes/{index}'

    async def _create_index(self, index: str):
        url = self.host + '/indexes'
        payload = {
            "override_if_exists": True,
            "index": {
                "name": index,
                "storage_type": "filesystem",
                'fields': {f.field: get_lnx_field(f) for f in search_index_fields},
                # https://github.com/miyachan/torako/blob/master/src/storage/search_lnx/posts.json
                # "fields": {
                #     "property1": {
                #         "type": "f64",
                #         "stored": True,
                #         "indexed": True,
                #         "multi": False,
                #         "fast": False
                #     }
                # },
                'search_fields': ['title', 'comment'],
                "boost_fields": {},
                "reader_threads": 16,
                "max_concurrency": 4,
                "writer_buffer": 144000000,
                "writer_threads": 4,
                "set_conjunction_by_default": True,  # default AND instead of OR for queries
                "use_fast_fuzzy": False,  # only exact match
                "strip_stop_words": False,  # keep words like 'the' 'with'
                "auto_commit": 1,
            },
        }
        resp = await self.client.post(url, data=dumps(payload))
        resp = loads(await resp.read())
        # print(resp)
        await self._commit_write(index)
        # return loads(await resp.read())

    async def _index_clear(self, index: str):
        url = self._get_index_url(index) + '/documents/clear'
        resp = await self.client.delete(url)
        return loads(await resp.read())

    async def _index_delete(self, index: str):
        url = self._get_index_url(index)
        resp = await self.client.delete(url)
        await self._commit_write(index)
        # return loads(await resp.read())

    async def _index_ready(self, index: str):
        return True

    async def _index_stats(self, index: str):
        url = self._get_index_url(index) + '/stats'
        resp = await self.client.get(url)
        return loads(await resp.read())

    async def _add_docs(self, index: str, docs: list[any]):
        await self._remove_docs(index, get_doc_pks(docs))
        url = self._get_index_url(index) + '/documents'
        docs = [{k: [str(v)] for k, v in d.items()} for d in docs]
        resp = await self.client.post(url, data=dumps(docs))
        await self._commit_write(index)
        # return loads(await resp.read())

    async def _remove_docs(self, index: str, pk_ids: list[str]):
        if not pk_ids: return
        url = self._get_index_url(index) + '/documents'
        resp = await self.client.delete(url, data=dumps({pk: pk_ids}))
        resp = loads(await resp.read())
        await self._commit_write(index)
        return resp

    async def _commit_write(self, index: str):
        url = self._get_index_url(index) + '/commit'
        resp = await self.client.post(url)
        return loads(await resp.read())

    async def _search_index(self, index: str, q: SearchQuery):
        url = self._get_index_url(index) + '/search'
        payload = {
            'query': self._query_builder(q),
            'limit': q.result_limit,
            'offset': 0 if q.page == 1 else (q.page - 1) * q.result_limit,
            'order_by': q.sort_by,
            'sort': q.sort,
        }
        resp = await self.client.post(url, data=dumps(payload))
        parsed = loads(await resp.read())['data']
        if 'count' not in parsed:
            print(parsed)
            return [], 0

        total = parsed.get('count', 0)
        hits = [_restore_result(r['doc']) for r in parsed['hits']]
        return hits, total

    def _query_builder(self, q: SearchQuery):
        query = []
        if q.terms:
            query.append({'occur': 'must', 'term': {'ctx': q.terms, 'fields': ['comment', 'title']}})
        if q.boards:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'{" OR ".join(f"board:{b}" for b in q.boards)}',
                        # 'ctx': f'({" ".join(f"{b}" for b in q.boards)})',
                        # 'ctx': f" OR ".join(q.boards),
                        # 'ctx': f'board: IN [{" ".join(q.boards)}]',
                    },
                }
            )
        if q.before is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'timestamp:<{q.before}',
                    },
                }
            )
        if q.after is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'timestamp:>{q.after}',
                    },
                }
            )
        if q.num is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'num:{q.num}',
                    },
                }
            )
        if q.op is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'op:{str(q.op)}',
                    },
                }
            )
        if q.deleted is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'deleted:{str(q.deleted)}',
                    },
                }
            )
        if q.has_file is not None or q.has_no_file is not None:
            query.append(
                {
                    'occur': 'mustnot' if q.has_file or q.has_no_file == False else 'must',
                    'normal': {
                        'ctx': f'media_filename:None',
                        # 'ctx': f'{"" if q.has_file else "-"}(media_filename:None)',
                    },
                }
            )
        if q.media_hash is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'media_hash:{q.media_hash}',
                    },
                }
            )
        if q.media_file is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'media_filename:{q.media_file}',
                    },
                }
            )
        # print(query)
        return query


def get_lnx_field(field: SearchIndexField):
    ftype = _get_field_type(field)
    lnx_field = {
        'type': ftype,
        'stored': True,
    }
    not_text = ftype not in ('string', 'text')
    filt_sort = any((field.filterable, field.sortable))
    if not_text and filt_sort:
        lnx_field['indexed'] = True
        lnx_field['fast'] = False
    if field.sortable:
        lnx_field['fast'] = True
    return lnx_field


def _get_field_type(field: SearchIndexField):
    if field.searchable:
        return 'text'
    elif field.field_type is str:
        return 'string'
    elif field.field_type is int:
        return 'u64'
    elif field.field_type is float:
        return 'f64'
    elif field.field_type is bool:
        return 'string'


def _restore_result(doc: dict):
    if doc['comment'] == 'None':
        doc['comment'] = None
    return {'comment': doc['comment'], **loads(doc['data'])}
