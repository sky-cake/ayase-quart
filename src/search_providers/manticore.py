import aiomysql
from orjson import loads

from .baseprovider import BaseSearch
from . import (
	SearchQuery,
	SearchIndexField,
	POST_PK,
	search_index_fields,
	hl_pre,
	hl_post,
	MAX_RESULTS,
)

pk = POST_PK

class ManticoreSearch(BaseSearch):
	pool: aiomysql.Pool

	def __init__(self, *arg, **kwargs):
		super().__init__(*arg, **kwargs)
		conf = kwargs['config']
		self.pool = aiomysql.create_pool(
			host=self.host,
			autocommit=True,
			**conf,
		)

	async def _execute_query(self, query: str, params: tuple[any]=None):
		async with self.pool.acquire() as connection:
			async with connection.cursor() as cursor:
				await cursor.execute(query, params)
				results = []
				results.append(await cursor.fetchall())
				while not await cursor.nextset():
					results.append(await cursor.fetchall())
				if len(results) == 1:
					return results[0]
				return results

	async def _create_index(self, index: str):
		columns = ', '.join(f'{f.field} {_get_field_type(f)}' for f in search_index_fields)
		table_opts = [
			"engine='columnar'",
		]
		q = f"create table {index} ({columns}) {' '.join(table_opts)};"
		return await self._execute_query(q)

	async def _index_clear(self, index: str):
		q = f'TRUNCATE TABLE {index};'
		return await self._execute_query(q)

	async def _index_delete(self, index: str):
		q = f'DROP TABLE IF EXISTS {index};'
		return await self._execute_query(q)

	async def _index_ready(self, index: str):
		return True

	async def _add_docs(self, index: str, docs: list[any]):
		columns = [f.field for f in search_index_fields]
		vals = [tuple(d[c] for c in columns) for d in docs]
		q = f'insert into {index}({",".join(columns)}) values {",".join("%s" for _ in docs)};'
		return await self._execute_query(q, (*vals,))

	async def _remove_docs(self, index: str, pk_ids: list[str]):
		pk_ids = tuple(pk_ids)
		q = f'delete from {index} where {pk} in %s;'
		return await self._execute_query(q, (pk_ids,))

	async def _search_index(self, index: str, q: SearchQuery):
		query_end = self._query_builder(q)
		q = f'select comment, data from {index} where {query_end}; show meta;'
		res, meta = await self._execute_query(q)
		total = [row[1] for row in meta if row[0] == 'total_found'][0]
		res = [{'comment': r[0], **loads(r[1])} for r in res]
		return res, total

	def _query_builder(self, q: SearchQuery):
		where_q = []
		where_q.append(f'board IN [{", ".join(q.boards)}]')
		if q.num is not None:
			where_q.append(f'num = {q.num}')
		if q.media_file is not None:
			where_q.append(f'media_filename = {q.media_file}')
		if q.media_hash is not None:
			where_q.append(f'media_hash = {q.media_hash}')
		if q.op is not None:
			where_q.append(f'op = {str(q.op).lower()}')
		if q.deleted is not None:
			where_q.append(f'deleted = {str(q.deleted).lower()}')
		if q.file is not None:
			where_q.append(f'{"NOT" if q.file else ""} media_filename IS NULL')
		if q.before is not None:
			where_q.append(f'timestamp < {q.before}')
		if q.after is not None:
			where_q.append(f'timestamp > {q.after}')

		page_q = []
		if q.sort_by:
			page_q.append(f'order_by {q.sort_by} {q.sort}')
		page_q.append(f'limit {q.result_limit}')
		if q.page > 1:
			page_q.append(f'offset {q.result_limit * q.page}')
		return f"{' and '.join(where_q)} {' '.join(page_q)}"

def _get_field_type(field: SearchIndexField):
	if field.searchable:
		return 'text'
	elif field.type is str:
		return 'string'
	elif field.type is int:
		return 'int'
	elif field.type is float:
		return 'float'
	elif field.type is bool:
		return 'bool'