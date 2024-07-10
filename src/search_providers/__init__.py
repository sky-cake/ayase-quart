from dataclasses import dataclass
from typing import Optional
from zlib import compress, decompress
from base64 import b64decode, b64encode

from orjson import dumps, loads

from configs import CONSTS

hl_pre = '||sr_hl_cls_start||'
hl_post = '||sr_hl_cls_end||'

POST_PK = 'pk'
MAX_RESULTS = CONSTS.max_result_limit

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
	result_limit: int = CONSTS.default_result_limit
	page: Optional[int] = 1
	sort: str = 'asc'
	sort_by: Optional[str] = 'timestamp'
	spoiler: Optional[bool] = None
	highlight: bool = True

@dataclass(slots=True)
class SearchIndexField:
	field: str
	field_type: type
	optional: bool = False
	sortable: bool = False
	searchable: bool = False
	filterable: bool = False

search_index_fields = [
	SearchIndexField('pk', str, filterable=True),
	SearchIndexField('title', str, searchable=True, optional=True),
	SearchIndexField('comment', str, searchable=True, optional=True),
	SearchIndexField('board', str, filterable=True),
	SearchIndexField('thread_num', int, filterable=True),
	SearchIndexField('media_filename', str, filterable=True, optional=True),
	SearchIndexField('media_hash', str, filterable=True, optional=True),
	SearchIndexField('num', int, filterable=True),
	SearchIndexField('timestamp', int, sortable=True, filterable=True),
	SearchIndexField('op', bool, filterable=True),
	SearchIndexField('deleted', bool, filterable=True),
	SearchIndexField('data', str),
]

def get_search_provider():
	match CONSTS.index_search_provider:
		case 'mysql':
			from .mysql import MysqlSearch as Search_p
		case 'meili':
			from .meili import MeiliSearch as Search_p
		case 'typesense':
			from .typesense import TypesenseSearch as Search_p
		case 'manticore':
			from .manticore import ManticoreSearch as Search_p
		case 'lnx':
			from .lnx import LnxSearch as Search_p
		case _:
			from .mysql import MysqlSearch as Search_p

	search_p = Search_p(CONSTS.index_search_host, CONSTS.index_search_config)
	return search_p

# https://www.meilisearch.com/docs/guides/performance/indexing_best_practices#optimize-document-size
def compress_data(data: dict):
	return b64encode(compress(dumps(data), level=9, wbits=-15)).decode()

def decompress_data(data: str):
	return loads(decompress(b64decode(data), wbits=-15, bufsize=2048))