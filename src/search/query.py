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
    if page := params.get('page'):
        if type(page) in (int, float):
            q.page = min(max(abs(int(page)), 1), 100)
    return q
