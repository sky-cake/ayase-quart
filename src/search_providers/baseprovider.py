from abc import ABC
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

import httpx


class INDEXES(StrEnum):
	posts = 'posts'
	# threads = 'threads'

POST_PK = 'doc_id'

@dataclass(slots=True)
class SearchIndex:
	index: str
	pk: str
	fields: list[str]
	search_fields: list[str]

@dataclass(slots=True)
class SearchQuery:
	terms: str
	boards: list[str]
	num: Optional[int] = None
	media_file: Optional[str] = None
	media_hash: Optional[str] = None
	before: Optional[int] = None
	after: Optional[int] = None
	file: Optional[bool] = None
	deleted: Optional[bool] = None
	op: Optional[bool] = None

class BaseSearch(ABC):
	host: str
	client: httpx.AsyncClient

	def __init__(self, host: str, config: dict=None):
		self.host = host
		self.client = httpx.AsyncClient(headers=config.get('headers', None), timeout=900)

	async def close(self):
		await self.client.close()

	async def _create_index(self, index: str, pk: str):
		raise NotImplementedError

	async def _search_index(self, index: str, q: SearchQuery):
		raise NotImplementedError

	async def _index_clear(self, index: str):
		raise NotImplementedError

	async def _index_delete(self, index: str):
		raise NotImplementedError

	async def _index_ready(self, index: str):
		raise NotImplementedError

	async def _add_docs(self, index: str, pk: str, docs: list[any]):
		raise NotImplementedError

	async def _remove_docs(self, index: str, pk: str, doc_ids: list[int]):
		raise NotImplementedError

	# async def search_threads(self, q: SearchQuery) -> list[ThreadResult]:
	# 	await self._search_index(INDEXES.threads)

	async def index_ready(self, index: str):
		return (await self._index_ready(index)) == 'ready'

	async def search_posts(self, q: SearchQuery):
		return await self._search_index(INDEXES.posts, q)

	async def add_posts(self, posts: list[any]):
		await self._add_docs(INDEXES.posts, POST_PK, posts)

	async def remove_posts(self, doc_ids: list[int]):
		await self._remove_docs(INDEXES.posts, POST_PK, doc_ids)

	async def posts_ready(self):
		return await self._index_ready(INDEXES.posts)

	async def posts_wipe(self):
		return await self._index_delete(INDEXES.posts)

	async def init_indexes(self):
		await self._create_index(INDEXES.posts, POST_PK)