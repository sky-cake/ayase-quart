from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from configs import CONSTS
from .post_metadata import board_2_int
from posts.capcodes import capcode_2_id
from utils.validation import positive_int

@dataclass(slots=True)
class SearchQuery:
    terms: str
    boards: list[int]
    num: Optional[int] = None
    media_file: Optional[str] = None
    media_hash: Optional[str] = None
    width: Optional[int] = 0
    height: Optional[int] = 0
    capcode: Optional[int] = None
    before: Optional[int] = None
    after: Optional[int] = None
    has_file: Optional[bool] = None
    has_no_file: Optional[bool] = None
    deleted: Optional[bool] = None
    op: Optional[bool] = None
    sticky: Optional[bool] = None
    result_limit: int = CONSTS.default_result_limit
    page: Optional[int] = 1
    sort: str = 'asc'
    sort_by: Optional[str] = 'timestamp'
    spoiler: Optional[bool] = None
    highlight: bool = False

common_words = set('the be to of and a in that have I it for not on with he as you do at this but his by from they we say her she or an will my one all would there their what so up out if about who get which go me when make can like time no just him know take people into year your good some could them see other than then now look only come its over think also back after use two how our work first well way even new want because any these give day most us'.split())

def get_search_query(params: dict) -> SearchQuery:
    terms = params['title'] or params['comment']

    q = SearchQuery(
        terms=terms,
        boards=[board_2_int(board) for board in params['boards']],
    )

    if params['num']:
        q.num = int(params['num'])
    if params['result_limit']:
        q.result_limit = positive_int(params['result_limit'], below=CONSTS.max_result_limit)
    if params['media_filename']:
        q.media_file = params['media_filename']
    if params['media_hash']:
        q.media_hash = params['media_hash']
    if params['has_file']:
        q.has_file = True
    if params['has_no_file']:
        q.has_no_file = True
    if params['width']:
        q.width = positive_int(params['width'])
    if params['height']:
        q.height = positive_int(params['height'])
    if params['user'] != 'any':
        q.capcode = capcode_2_id(params['user'])
    if params['is_op']:
        q.op = True
    if params['is_not_op']:
        q.op = False
    if params['is_deleted']:
        q.deleted = True
    if params['is_not_deleted']:
        q.deleted = False
    if params['is_sticky']:
        q.sticky = True
    if params['is_not_sticky']:
        q.sticky = False
    if params['date_after']:
        dt = datetime.combine(params['date_after'], datetime.min.time())
        q.after = int(dt.timestamp())
    if params['date_before']:
        dt = datetime.combine(params['date_before'], datetime.min.time())
        q.before = int(dt.timestamp())
    if params['order_by'] in ('asc', 'desc'):
        q.sort = params['order_by']
    if page := params.get('page'):
        if type(page) in (int, float, str):
            q.page = positive_int(page, 1)
    return q
