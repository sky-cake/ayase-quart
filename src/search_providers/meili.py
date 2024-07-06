from orjson import dumps, loads

from .baseprovider import POST_PK, BaseSearch, SearchQuery


class MeiliSearch(BaseSearch):
    def __init__(self, *arg, **kwargs):

        super().__init__(*arg, **kwargs)

    def _get_index_url(self, index: str):
        return f'{self.host}/indexes/{index}'
    
    async def _create_index(self, index: str, pk: str):
        url = self.host + '/indexes'
        payload = {
            'uid': index,
            'primaryKey': pk,
        }
        await self.client.post(
            url,
            data=dumps(payload),
        )

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

    async def _search_index(self, index: str, q: SearchQuery):
        url = self._get_index_url(index) + '/search'
        filters = self._filter_builder(q)
        payload = {
            'matchingStrategy': 'all',
            'attributesToRetrieve': ['_formatted', 'data'],
            'attributesToCrop':["data:1"],
            'filter': filters,
            # 'sort': ['board:desc', 'timestamp:desc'],
            'limit': q.result_limit,
            "attributesToHighlight": ["title", 'comment'],
            "highlightPreTag": "||sr_hl_cls_start||",
            "highlightPostTag": "||sr_hl_cls_end||",
            # "highlightPreTag": "<span class=\"search_highlight_comment\">",
            # "highlightPostTag": "</span>",
        }

        if q.terms:
            payload.update({'q': q.terms})

        resp = await self.client.post(url, data=dumps(payload))
        data = loads(resp.read())
        return data.get('hits', [])

    async def _add_docs(self, index: str, pk: str, docs: list[any]):
        url = self._get_index_url(index) + '/documents'
        params = {
            'primaryKey': pk
        }
        await self.client.post(
            url,
            params=params,
            data=dumps(docs),
        )

    async def _remove_docs(self, index: str, pk: str, pk_ids: list[int]):
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
        return loads(resp.read())

    def _filter_builder(self, q: SearchQuery):
        filters = []
        filters.append(f'board IN [{", ".join(q.boards)}]')
        if q.num is not None:
            filters.append(f'num = {q.num}')
        if q.media_file is not None:
            filters.append(f'media_filename = {q.media_file}')
        if q.media_hash is not None:
            filters.append(f'media_hash = {q.media_hash}')
        if q.op is not None:
            filters.append(f'op = {str(q.op).lower()}')
        if q.deleted is not None:
            filters.append(f'deleted = {str(q.deleted).lower()}')
        if q.file is not None:
            filters.append(f'{"NOT" if q.file else ""} media_filename IS NULL')
        if q.before is not None:
            filters.append(f'timestamp < {q.before}')
        if q.after is not None:
            filters.append(f'timestamp > {q.after}')
        return filters

    async def _configure_index(self, index: str, pk: str, search_attrs: list[str], filter_attrs: list[str], sort_attrs: list[str]):
        b_url = self._get_index_url(index)
        conf = dict(
            displayedAttributes=['*'], # return all fields
            distinctAttribute=pk, # not sure what this is
            searchableAttributes=search_attrs, # only index the data_field
            filterableAttributes=filter_attrs, # only index the data_field
            sortableAttributes=sort_attrs,
            # nonSeparatorTokens=[], # remove default sep tokens
            separatorTokens=['.', '/', '"', "'", '-'], # add sep tokens
            rankingRules=['sort'], # remove default ranking rules
            searchCutoffMs=20000, # time before search gives up
            typoTolerance= dict(
                enabled=False # disable typo
            ),
            pagination=dict(
                maxTotalHits=10000 # increase max hits
            ),
        )
        resp = await self.client.patch(f'{b_url}/settings', data=dumps(conf))
        return loads(resp.read())

    async def config_posts(self):
        search_attrs = ['title', 'comment']
        filter_attrs = ['board', 'thread_num', 'title', 'comment', 'media_filename', 'media_hash', 'num', 'timestamp', 'op', 'deleted',]
        sort_attrs = ['timestamp', 'board']
        return await self._configure_index('posts', POST_PK, search_attrs, filter_attrs, sort_attrs)