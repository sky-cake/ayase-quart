from configs import CONSTS

from .baseprovider import SearchQuery


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