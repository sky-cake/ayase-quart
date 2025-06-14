from dataclasses import dataclass

from configs import index_search_conf
from enums import IndexSearchType

from ..query import IndexSearchQuery  # noqa: F401

POST_PK = 'pk'

@dataclass(slots=True)
class SearchIndexField:
    field: str
    field_type: type
    optional: bool = False
    sortable: bool = False
    searchable: bool = False
    filterable: bool = False


search_index_fields = [
    SearchIndexField('pk', int, filterable=True),
    SearchIndexField('title', str, searchable=True, optional=True),
    SearchIndexField('comment', str, searchable=True, optional=True),
    SearchIndexField('board', int, filterable=True),
    SearchIndexField('media_filename', str, filterable=True, optional=True),
    SearchIndexField('title_length', int, filterable=True, optional=True),
    SearchIndexField('comment_length', int, filterable=True, optional=True),
    SearchIndexField('media_hash', str, filterable=True, optional=True),
    SearchIndexField('trip', str, filterable=True, optional=True),
    SearchIndexField('num', int, sortable=True, filterable=True),
    SearchIndexField('thread_num', int, filterable=True, optional=True),
    SearchIndexField('media_w', int, filterable=True, optional=True),
    SearchIndexField('media_h', int, filterable=True, optional=True),
    SearchIndexField('timestamp', int, sortable=True, filterable=True),
    SearchIndexField('op', bool, filterable=True),
    SearchIndexField('deleted', bool, filterable=True),
    SearchIndexField('capcode', int, filterable=True),
    SearchIndexField('sticky', bool, filterable=True),
    SearchIndexField('data', str),
]

if index_search_conf.get('use_file_archived'):
    search_index_fields += [
        SearchIndexField('file_archived', bool, filterable=True, optional=True),
        SearchIndexField('media_orig', str, filterable=True, optional=True),
    ]


def get_index_search_provider():
    if hasattr(get_index_search_provider, 'search_p'):
        return get_index_search_provider.search_p
    match IndexSearchType[index_search_conf['provider']]:
        case IndexSearchType.meili:
            from .meili import MeiliSearch as Search_p
        case IndexSearchType.typesense:
            from .typesense import TypesenseSearch as Search_p
        case IndexSearchType.manticore:
            from .manticore import ManticoreSearch as Search_p
        case IndexSearchType.lnx:
            from .lnx import LnxSearch as Search_p
        case IndexSearchType.quickwit:
            from .quickwit import QuickwitSearch as Search_p
        case _:
            from .lnx import LnxSearch as Search_p

    search_p = Search_p(index_search_conf)
    get_index_search_provider.search_p = search_p
    return search_p
