from abc import ABC
from dataclasses import dataclass
from enum import StrEnum

from aiohttp import ClientSession, TCPConnector

from . import SearchQuery

class INDEXES(StrEnum):
	posts = 'posts'
	# threads = 'threads'

@dataclass(slots=True)
class SearchIndex:
	index: str
	pk: str
	fields: list[str]
	search_fields: list[str]

class BaseSearch(ABC):
	host: str
	client: ClientSession

	def __init__(self, host: str, config: dict=None):
		self.host = host
		# self.client = httpx.AsyncClient(headers=config.get('headers', None), timeout=900)
		self.client = ClientSession(
			connector=TCPConnector(keepalive_timeout=900),
			headers=config.get('headers', None),
			# timeout=None
		)
		
	async def close(self):
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

	async def _add_docs(self, index: str, docs: list[any]):
		raise NotImplementedError

	async def _remove_docs(self, index: str, pk_ids: list[str]):
		raise NotImplementedError

	async def _search_index(self, index: str, q: SearchQuery) -> tuple[list[any], int]:
		raise NotImplementedError

	async def index_ready(self, index: str):
		return (await self._index_ready(index)) == 'ready'

	# returns search results + num hits. upstream calculates pages from cur_page + limits
	async def search_posts(self, q: SearchQuery) -> tuple[list[dict], int]:
		results, total_hits =  await self._search_index(INDEXES.posts, q)
		return results, total_hits

	async def add_posts(self, posts: list[dict]):
		await self._add_docs(INDEXES.posts, posts)

	async def remove_posts(self, doc_ids: list[int]):
		await self._remove_docs(INDEXES.posts, doc_ids)

	async def posts_ready(self):
		return await self._index_ready(INDEXES.posts)

	async def posts_wipe(self):
		return await self._index_delete(INDEXES.posts)

	async def init_indexes(self):
		await self._create_index(INDEXES.posts)

	async def post_stats(self):
		return await self._index_stats(INDEXES.posts)