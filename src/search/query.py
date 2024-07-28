from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from configs import CONSTS, IndexSearchType


@dataclass(slots=True)
class SearchQuery:
	terms: str
	boards: list[str]
	num: Optional[int] = None
	media_file: Optional[str] = None
	media_hash: Optional[str] = None
	before: Optional[int] = None
	after: Optional[int] = None
	has_file: Optional[bool] = None
	has_no_file: Optional[bool] = None
	deleted: Optional[bool] = None
	op: Optional[bool] = None
	result_limit: int = CONSTS.default_result_limit
	page: Optional[int] = 1
	sort: str = 'asc'
	sort_by: Optional[str] = 'timestamp'
	spoiler: Optional[bool] = None
	highlight: bool = False


def get_search_query(params: dict) -> SearchQuery:
    terms = params['title'] or params['comment']

    # this needs time to sort out and test
    # should consider using search engine apis so we dont need to worry about security
    chars_to_escape = []
    match CONSTS.index_search_provider:
        case IndexSearchType.manticore:
            # https://manual.manticoresearch.com/Searching/Full_text_matching/Escaping#Escaping-characters-in-query-string
            chars_to_escape = ['\\', '!', '"', '$', "'", '(', ')', '-', '/', '<', '@', '^', '|', '~']

        case IndexSearchType.meili:
            # https://www.meilisearch.com/docs/reference/api/search#query-q
            # seems ok with any chars, did testing
            chars_to_escape = []

        case IndexSearchType.lnx:
            # https://docs.lnx.rs/#tag/Run-searches/operation/Search_Index_indexes__index__search_post
            # seems ok with any chars, needs testing
            chars_to_escape = []

        case IndexSearchType.typesense:
            # https://typesense.org/docs/26.0/api/search.html#search-parameters
            # seems ok with any chars, needs testing
            chars_to_escape = []
            if not terms:
                terms = '*' # return all

    for char in chars_to_escape:
        terms = terms.replace(char, '\\' + char) # e.g. @ becomes \@

    q = SearchQuery(
        terms=terms,
        boards=params['boards'],
    )

    if params['num']:
        q.num = int(params['num'])
    if params['result_limit']:
        q.result_limit = min(int(params['result_limit']), CONSTS.max_result_limit)
    if params['media_filename']:
        q.media_file = params['media_filename']
    if params['media_hash']:
        q.media_hash = params['media_hash']
    if params['has_file']:
        q.has_file = True
    if params['has_no_file']:
        q.has_no_file = True
    if params['is_op']:
        q.op = True
    if params['is_not_op']:
        q.op = False
    if params['is_deleted']:
        q.deleted = True
    if params['is_not_deleted']:
        q.deleted = False
    if params['date_after']:
        dt = datetime.combine(params['date_after'], datetime.min.time())
        q.after = int(dt.timestamp())
    if params['date_before']:
        dt = datetime.combine(params['date_before'], datetime.min.time())
        q.before = int(dt.timestamp())
    if params['order_by'] in ('asc', 'desc'):
        q.sort = params['order_by']

    return q