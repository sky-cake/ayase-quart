from orjson import dumps, loads

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

class LnxSearch(BaseSearch):
	def __init__(self, *arg, **kwargs):
		super().__init__(*arg, **kwargs)

	def _get_index_url(self, index: str):
		return f'{self.host}/indexes/{index}'

	async def _create_index(self, index: str):
		url = self.host + 'indexes'
		payload = {
			"override_if_exists": False,
			"index": {
				"name": index,
				"storage_type": "filesystem",
				'fields': {f.field: _get_field_type(f) for f in search_index_fields},
				# https://github.com/miyachan/torako/blob/master/src/storage/search_lnx/posts.json
				# "fields": {
				# 	"property1": {
				# 		"type": "f64",
				# 		"stored": True,
				# 		"indexed": True,
				# 		"multi": False,
				# 		"fast": False
				# 	}
				# },
				'search_fields': ['title', 'comment'],
				"boost_fields": {},
				"reader_threads": 16,
				"max_concurrency": 4,
				"writer_buffer": 300000,
				"writer_threads": 0,
				"set_conjunction_by_default": False,
				"use_fast_fuzzy": False,
				"strip_stop_words": False,
				"auto_commit": 0
			}
		}
		resp = await self.client.post(url, data=dumps(payload))
		return loads(resp.read())

	async def _index_clear(self, index: str):
		url = self._get_index_url(index) + '/documents/clear'
		resp = await self.client.delete(url)
		return loads(resp.read())

	async def _index_delete(self, index: str):
		url = self._get_index_url(index)
		resp = await self.client.delete(url)
		return loads(resp.read())

	async def _index_ready(self, index: str):
		raise NotImplementedError

	async def _add_docs(self, index: str, docs: list[any]):
		url = self._get_index_url(index) + '/documents'
		resp = await self.client.post(url, data=dumps(docs))
		return loads(resp.read())

	async def _remove_docs(self, index: str, pk_ids: list[str]):
		if not pk_ids:
			return
		url = self._get_index_url(index) + '/documents'
		resp = await self.client.delete(url, data=dumps({pk: pk_ids}))
		return loads(resp.read())

	async def _search_index(self, index: str, q: SearchQuery):
		url = self._get_index_url(index) + '/search'
		payload = {
			'query': q.terms,
			'limit': q.result_limit,
			'offset': 0 if q.page == 1 else (q.page-1) * q.result_limit,
			'order_by': q.order_by,
			'sort': q.sort,
		}
		if q.page > 1:
			payload['offset'] = q.page * q.result_limit
		resp = await self.client.post(url, data=dumps(payload))
		parsed = dumps(resp.read())
		hits = parsed.get('data', {}).get('hits', [])
		total = parsed.get('data', {}).get('total', 0)
		return hits, total

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
		lnx_field['fast'] = 'single'
	return lnx_field

def _get_field_type(field: SearchIndexField):
	if field.searchable:
		return 'text'
	elif field.type is str:
		return 'string'
	elif field.type is int:
		return 'u64'
	elif field.type is float:
		return 'f64'
	elif field.type is bool:
		return 'u32'