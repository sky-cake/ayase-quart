from abc import ABC
from dataclasses import dataclass
from collections import defaultdict
from enum import StrEnum
from typing import Any, Callable, Generator

from aiohttp import ClientSession, TCPConnector
from orjson import dumps

from search.post_metadata import unpack_metadata

from . import SearchQuery


class INDEXES(StrEnum):
    posts = 'posts'


@dataclass(slots=True)
class SearchIndex:
    index: str
    pk: str
    fields: list[str]
    search_fields: list[str]


class BaseSearch(ABC):
    host: str
    client: ClientSession

    def __init__(self, host: str, config: dict = None):
        self.host = host.strip('/')
        self.client = ClientSession(
            connector=TCPConnector(keepalive_timeout=600),
            headers=config.get('headers', None),
        )

    async def close(self):
        if not self.client.closed:
            await self.client.close()

    async def _create_index(self, index: str):
        raise NotImplementedError

    async def _index_clear(self, index: str):
        raise NotImplementedError

    async def _index_delete(self, index: str):
        raise NotImplementedError

    async def _index_ready(self, index: str):
        raise NotImplementedError

    async def _index_stats(self, index: str):
        raise NotImplementedError

    async def _add_docs(self, index: str, docs: list[Any]):
        raise NotImplementedError

    async def _add_docs_bytes(self, index: str, docs: bytes):
        raise NotImplementedError

    async def _remove_docs(self, index: str, pk_ids: list[str]):
        raise NotImplementedError

    async def _search_index(self, index: str, q: SearchQuery) -> tuple[Generator[any, None, None], int]:
        raise NotImplementedError

    def _get_post_pack_fn(self) -> Callable[[dict], dict]:
        return lambda post: post

    def _get_batch_pack_fn(self) -> Callable[[dict], bytes]:
        return dumps
    
    def _finalize(self, index: str):
        pass

    async def index_ready(self, index: str):
        return (await self._index_ready(index)) == 'ready'

    async def search_posts(self, q: SearchQuery) -> tuple[list[dict], int]:
        """Returns search results and num hits.
        Downstream calculates pages from cur_page and limits.
        Comments have not been restored using `restore_comment()`.
        """
        results, total_hits = await self._search_index(INDEXES.posts.value, q)
        # results = [{'comment':r['comment'], **unpack_metadata(r['data'])} for r in results]
        results = [unpack_metadata(r['data'], r['comment']) for r in results]
        return results, total_hits

    async def search_posts_get_thread_nums(self, q: SearchQuery, form_data: dict) -> dict:
        """Returns {board_shortname: thread_nums} mappings.
        Used for faceted search.
        """
        q.op = True
        q.terms = (form_data['op_title'] + ' ' + form_data['op_comment']).strip()

        results, _ = await self._search_index(INDEXES.posts.value, q)
        results = [unpack_metadata(r['data'], '') for r in results] # must unpack everything to get op_nums
        d = defaultdict(list)
        for p in results:
            d[p['board_shortname']].append(p['num'])
        return d

    async def add_posts(self, posts: list[dict]):
        await self._add_docs(INDEXES.posts.value, posts)

    def get_post_pack_fn(self):
        return self._get_post_pack_fn()

    def get_batch_pack_fn(self):
        return self._get_batch_pack_fn()

    async def add_posts_bytes(self, posts: bytes):
        await self._add_docs_bytes(INDEXES.posts.value, posts)

    async def remove_posts(self, doc_ids: list[int]):
        await self._remove_docs(INDEXES.posts.value, doc_ids)

    async def posts_ready(self):
        return await self._index_ready(INDEXES.posts.value)

    async def posts_wipe(self):
        return await self._index_delete(INDEXES.posts.value)

    async def init_indexes(self):
        await self._create_index(INDEXES.posts.value)

    async def post_stats(self):
        return await self._index_stats(INDEXES.posts.value)
    
    async def finalize(self):
        await self._finalize(INDEXES.posts.value)


"""
For deleting entries in indexes before adding them
in engines that don't support unique primary keys
TODO: Perhaps we need a utils.py file for all the providers...
"""
def get_doc_pks(docs: list[Any]):
    return [d['pk'] for d in docs]