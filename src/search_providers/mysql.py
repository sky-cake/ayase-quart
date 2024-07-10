from .baseprovider import BaseSearch
from . import SearchQuery


class MysqlSearch(BaseSearch):
	# asagi_converter:L160
	def __init__(self, *arg, **kwargs):
		super().__init__(*arg, **kwargs)

	async def _create_index(self, index: str, pk: str):
		pass

	async def _index_clear(self, index: str):
		pass

	async def _index_delete(self, index: str):
		pass

	async def _index_ready(self, index: str):
		return True

	async def _add_docs(self, index: str, pk: str, docs: list[any]):
		pass

	async def _remove_docs(self, index: str, pk: str, pk_ids: list[str]):
		pass

	async def _search_index(self, index: str, q: SearchQuery):
		q = f'''
		select from
		where
			match(comment, title) against (%s in natural language mode)
		order by
		limit
		;'''
		
