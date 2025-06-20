from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from posts.capcodes import Capcode, capcode_2_id
from utils.integers import clamp_positive_int

from configs import index_search_conf
from .post_metadata import board_2_int


@dataclass(slots=True)
class IndexSearchQuery:
    boards: list[int]
    comment: Optional[str] = None
    title: Optional[str] = None
    min_title_length: Optional[int] = None
    min_comment_length: Optional[int] = None
    num: Optional[int] = None
    nums: Optional[list[int]] = None
    thread_nums: Optional[list[int]] = None
    media_filename: Optional[str] = None
    media_hash: Optional[str] = None
    trip: Optional[str] = None
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
    hits_per_page: int = index_search_conf['hits_per_page']
    page: Optional[int] = 1
    sort: str = 'asc'
    sort_by: Optional[str] = 'timestamp'
    spoiler: Optional[bool] = None
    highlight: bool = False

    if index_search_conf.get('use_file_archived'):
        file_archived: Optional[bool] = None
        media_origs: Optional[list[str]] = None


common_words = set('the be to of and a in that have I it for not on with he as you do at this but his by from they we say her she or an will my one all would there their what so up out if about who get which go me when make can like time no just him know take people into year your good some could them see other than then now look only come its over think also back after use two how our work first well way even new want because any these give day most us'.split())


def get_index_search_query(params: dict, board_ints=None) -> IndexSearchQuery:
    q = IndexSearchQuery(
        comment=params['comment'],
        title=params['title'],
        boards=[board_2_int(board) for board in params['boards']] if not board_ints else board_ints,
    )

    if params.get('thread_nums'):
        q.thread_nums = params['thread_nums']

    if params.get('nums'):
        q.nums = params['nums']

    if params['num'] and not params.get('nums'):
        q.num = int(params['num'])

    if params.get('min_title_length'):
        q.min_title_length = params['min_title_length']

    if params.get('min_comment_length'):
        q.min_comment_length = params['min_comment_length']

    if index_search_conf.get('use_file_archived') and params.get('file_archived'):
        q.file_archived = True

    if index_search_conf.get('use_file_archived') and params.get('media_origs'):
        q.media_origs = params['media_origs']

    if params['hits_per_page']:
        q.hits_per_page = clamp_positive_int(params['hits_per_page'], 1, index_search_conf['hits_per_page'])
    if params['media_filename']:
        q.media_filename = params['media_filename']
    if params['media_hash']:
        q.media_hash = params['media_hash']
    if params['has_file']:
        q.has_file = True
    if params['has_no_file']:
        q.has_no_file = True
    if params['width']:
        q.width = clamp_positive_int(params['width'])
    if params['height']:
        q.height = clamp_positive_int(params['height'])
    if params['capcode'] != Capcode.default.value:
        q.capcode = capcode_2_id(params['capcode'])
    if params['tripcode']:
        q.trip = params['tripcode']
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
        q.page = page

    return q
