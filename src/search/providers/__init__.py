from base64 import b85decode, b85encode
from dataclasses import dataclass
from zlib import compress, decompress

from orjson import dumps, loads

from configs import CONSTS, IndexSearchType

from ..query import SearchQuery  # re-export

POST_PK = 'pk'
MAX_RESULTS = CONSTS.max_result_limit


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
	if hasattr(get_search_provider, 'search_p'):
		return get_search_provider.search_p
	match CONSTS.index_search_provider:
		case IndexSearchType.mysql:
			from .mysql import MysqlSearch as Search_p
		case IndexSearchType.meili:
			from .meili import MeiliSearch as Search_p
		case IndexSearchType.typesense:
			from .typesense import TypesenseSearch as Search_p
		case IndexSearchType.manticore:
			from .manticore import ManticoreSearch as Search_p
		case IndexSearchType.lnx:
			from .lnx import LnxSearch as Search_p
		case _:
			from .mysql import MysqlSearch as Search_p

	search_p = Search_p(CONSTS.index_search_host, CONSTS.index_search_config)
	get_search_provider.search_p = search_p
	return search_p

# https://www.meilisearch.com/docs/guides/performance/indexing_best_practices#optimize-document-size
def compress_data(data: dict):
	return b85encode(compress(dumps(data), level=9, wbits=-15)).decode()

def decompress_data(data: str):
	return loads(decompress(b85decode(data), wbits=-15, bufsize=2048))