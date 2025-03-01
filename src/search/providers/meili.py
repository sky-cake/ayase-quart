from orjson import dumps, loads

from search.highlighting import mark_post, mark_pre

from . import POST_PK, IndexSearchQuery, search_index_fields
from .baseprovider import INDEXES, BaseSearch
from configs import index_search_conf

pk = POST_PK


class MeiliSearch(BaseSearch):
    def __init__(self, *arg, **kwargs):

        super().__init__(*arg, **kwargs)

    def _get_index_url(self, index: str):
        return f'{self.host}/indexes/{index}'

    async def _create_index(self, index: str):
        url = self.host + '/indexes'
        payload = {
            'uid': index,
            'primaryKey': pk,
        }
        await self.client.post(
            url,
            data=dumps(payload),
        )
        await self._config_posts()

    async def _index_clear(self, index: str):
        url = self._get_index_url(index) + '/documents'
        await self.client.delete(url)

    async def _index_delete(self, index: str):
        url = self._get_index_url(index)
        await self.client.delete(url)

    async def _index_ready(self, index: str):
        url = self.host + '/stats'
        resp = loads((await self.client.get(url)).read())
        if not (index := resp['indexes'].get(index)):
            raise KeyError('Invalid Index')
        return not index['isIndexing']

    async def _index_stats(self, index: str):
        url = self.host + '/stats'
        resp = await self.client.get(url)
        return loads(await resp.read())

    async def _add_docs(self, index: str, docs: list[any]):
        url = self._get_index_url(index) + '/documents'
        params = {'primaryKey': pk}
        await self.client.post(
            url,
            params=params,
            data=dumps(docs),
        )

    async def _add_docs_bytes(self, index: str, docs: bytes):
        url = self._get_index_url(index) + '/documents'
        params = {'primaryKey': pk}
        await self.client.post(
            url,
            params=params,
            data=docs,
        )

    async def _remove_docs(self, index: str, pk_ids: list[str]):
        if not pk_ids:
            return
        url = self._get_index_url(index) + '/documents/delete'
        payload = {
            'filter': f'{pk} in [{", ".join(str(pk_id) for pk_id in pk_ids)}]',
        }
        resp = await self.client.post(
            url,
            data=dumps(payload),
        )
        return loads(await resp.read())

    async def _configure_index(self, index: str, pk: str, search_attrs: list[str], filter_attrs: list[str], sort_attrs: list[str]):
        b_url = self._get_index_url(index)
        conf = dict(
            displayedAttributes=['*'],  # return all fields
            distinctAttribute=pk,  # not sure what this is
            searchableAttributes=search_attrs,  # only index the data_field
            filterableAttributes=filter_attrs,  # only index the data_field
            sortableAttributes=sort_attrs,
            # nonSeparatorTokens=[], # remove default sep tokens
            separatorTokens=['.', '/', '"', "'", '-'],  # add sep tokens
            rankingRules=['sort'],  # remove default ranking rules
            searchCutoffMs=20_000,  # time before search gives up
            typoTolerance=dict(enabled=False),  # disable typo
            pagination=dict(
                maxTotalHits=index_search_conf['max_hits'],
            ),
        )
        resp = await self.client.patch(f'{b_url}/settings', data=dumps(conf))

        return loads(await resp.read())

    async def _config_posts(self):
        search_attrs = [f.field for f in search_index_fields if f.searchable]
        filter_attrs = [f.field for f in search_index_fields if f.filterable]
        sort_attrs = [f.field for f in search_index_fields if f.sortable]
        return await self._configure_index(INDEXES.posts.value, pk, search_attrs, filter_attrs, sort_attrs)

    async def _search_index(self, index: str, q: IndexSearchQuery):
        url = self._get_index_url(index) + '/search'
        filters = self._filter_builder(q)
        payload = {
            'matchingStrategy': 'all',
            # 'attributesToRetrieve': ['data', 'comment'],
            # 'attributesToCrop': ["data:1"],
            'filter': filters,
            'sort': [f'timestamp:{q.sort}'],
            'hitsPerPage': q.hits_per_page,
            'page': q.page,
        }

        if q.comment or q.title:
            payload['q'] = q.comment or q.title # can we separate these?

        if q.highlight:
            payload.update(
                {
                    "attributesToHighlight": ["title", 'comment'],
                    "highlightPreTag": mark_pre,
                    "highlightPostTag": mark_post,
                }
            )

        resp = await self.client.post(url, data=dumps(payload))
        data = loads(await resp.read())
        hits = (_restore_hit(h) for h in data.get('hits', []))
        if h2 := data.get('hits'):
            print(h2[0])
        total = data.get('totalHits', 0)
        return hits, total

    def _filter_builder(self, q: IndexSearchQuery):
        filters = []
        filters.append(f'board IN [{", ".join(q.boards)}]')
        if q.num is not None:
            filters.append(f'num = {q.num}')
        if q.media_file is not None:
            filters.append(f'media_filename = {q.media_file}')
        if q.media_hash is not None:
            filters.append(f'media_hash = {q.media_hash}')
        if q.trip is not None:
            filters.append(f'trip = {q.trip}')
        if q.width is not None:
            filters.append(f'media_w = {q.width}')
        if q.height is not None:
            filters.append(f'media_h = {q.height}')
        if q.capcode is not None:
            filters.append(f'capcode = {q.capcode}')
        if q.op is not None:
            filters.append(f'op = {int(q.op)}')
        if q.deleted is not None:
            filters.append(f'deleted = {int(q.deleted)}')
        if q.sticky is not None:
            filters.append(f'sticky = {int(q.sticky)}')
        if q.has_file:
            filters.append(f'(media_filename IS NOT EMPTY) AND (media_filename IS NOT NULL)')
        if q.has_no_file:
            filters.append(f'(media_filename IS EMPTY) OR (media_filename IS NULL)')
        if q.before is not None:
            filters.append(f'timestamp < {q.before}')
        if q.after is not None:
            filters.append(f'timestamp > {q.after}')
        return filters


def _restore_hit(hit: dict):
    # post = loads(hit['data'])
    # post['comment'] = hit['comment']
    # return post
    return hit
