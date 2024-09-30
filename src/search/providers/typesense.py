from typing import Any

from orjson import dumps, loads

from search.highlighting import mark_post, mark_pre

from . import (
    MAX_RESULTS,
    POST_PK,
    SearchIndexField,
    SearchQuery,
    search_index_fields
)
from .baseprovider import BaseSearch

pk = POST_PK


class TypesenseSearch(BaseSearch):
    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

    def _get_index_url(self, index: str):
        return f'{self.host}/collections/{index}'

    async def _create_index(self, index: str):
        url = f'{self.host}/collections'
        payload = {
            'name': index,
            'fields': [_get_field(f) for f in search_index_fields],
            'default_sorting_field': 'timestamp',
        }
        resp = await self.client.post(url, data=dumps(payload))
        return loads(await resp.read())

    async def _index_clear(self, index: str):
        url = self._get_index_url(index) + '/documents'
        resp = await self.client.delete(url, params={'filter_by': f'num > 0'})
        return loads(await resp.read())

    async def _index_delete(self, index: str):
        url = self._get_index_url(index)
        resp = await self.client.delete(url)
        return loads(await resp.read())

    async def _index_ready(self, index: str):
        return True

    async def _index_stats(self, index: str):
        url = self._get_index_url(index)
        resp = await self.client.get(url)
        return loads(await resp.read())

    def _get_batch_pack_fn(self):
        return lambda docs: b'\n'.join(dumps(doc) for doc in docs)

    async def _add_docs(self, index: str, docs: list[Any]):
        url = self._get_index_url(index) + '/documents/import'
        data = b'\n'.join(dumps(doc) for doc in docs)
        params = {'action': 'create'}
        resp = await self.client.post(url, params=params, data=data)
        return [loads(line) for line in await resp.read().splitlines()]

    async def _add_docs_bytes(self, index: str, docs: bytes):
        url = self._get_index_url(index) + '/documents/import'
        params = {'action': 'create'}
        await self.client.post(url, params=params, data=docs)

    async def _remove_docs(self, index: str, pk_ids: list[str]):
        url = self._get_index_url(index) + '/documents'
        params = {'filter_by': f'{pk}: [{",".join(pk_ids)}]'}
        resp = await self.client.delete(url, params=params)
        return loads(await resp.read())

    async def _search_index(self, index: str, q: SearchQuery):
        url = self._get_index_url(index) + '/documents/search'
        params = dict(
            collections=index,
            query_by='title,comment',
            filter_by=_build_filter(q),
            sort_by=f'timestamp:{q.sort}',
            include_fields='comment,data',
            page=q.page,
            per_page=q.result_limit,
            limit_hits=MAX_RESULTS,
            search_cutoff_ms=2_000,
            num_typos=0,
            split_join_tokens='off',
            # infix='always', # only 1 word...
            # use_cache=True,
            # cache_ttl=60,
        )
        if q.terms:
            params['q'] = q.terms
        if q.highlight:
            params.update(
                dict(
                    highlight_fields='comment',
                    highlight_full_fields='comment',
                    highlight_start_tag=mark_pre,
                    highlight_end_tag=mark_post,
                )
            )
        else:
            params['highlight_fields'] = 'none'
        resp = await self.client.get(url, params=params)
        data = loads(await resp.read())
        hits = [_restore_result(h, q.highlight) for h in data.get('hits', [])]
        total = data.get('found')
        return hits, total


def _build_filter(q: SearchQuery):
    filters = []
    filters.append(f'board: [{", ".join(q.boards)}]')
    if q.num is not None:
        filters.append(f'num := `{q.num}`')
    if q.media_file is not None:
        filters.append(f'media_filename := `{q.media_file}`')
    if q.media_hash is not None:
        filters.append(f'media_hash := `{q.media_hash}`')
    if q.op is not None:
        filters.append(f'op := {q.op}')
    if q.capcode is not None:
        filters.append(f'capcode := {q.capcode}')
    if q.deleted is not None:
        filters.append(f'deleted := {q.deleted}')
    if q.sticky is not None:
        filters.append(f'sticky := {q.sticky}')
    # typesense doesn't have null filtering yet
    # https://github.com/typesense/typesense/issues/790
    if q.file is not None:
        filters.append(f'media_filename :{"!" if q.file else ""}= `None`')
    if q.width is not None:
        filters.append(f'media_w := {q.width}')
    if q.height is not None:
        filters.append(f'media_w := {q.height}')
    if q.before is not None:
        filters.append(f'timestamp :< {q.before}')
    if q.after is not None:
        filters.append(f'timestamp :> {q.after}')
    return ' && '.join(filters)


def _get_field(field: SearchIndexField):
    ts_field = {
        'name': field.field,
        'type': _get_field_type(field),
    }
    if field.optional:
        ts_field['optional'] = True
    if not any((field.searchable, field.filterable, field.sortable)):
        ts_field['index'] = False
        ts_field['optional'] = True
    return ts_field


def _get_field_type(field: SearchIndexField):
    if field.field_type is str:
        return 'string'
    elif field.field_type is int:
        return 'int64'
    elif field.field_type is bool:
        return 'bool'


def _restore_result(result: dict, hl: bool):
    doc = result['document']
    if doc['comment'] == 'None':
        doc['comment'] = None
    if not hl:
        comment = doc.get('comment')
    else:
        if result['highlights']:
            comment = result['highlights'][0]['snippet']
        else:
            comment = None
    return {'comment': comment, **loads(doc['data'])}
