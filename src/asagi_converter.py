import asyncio
import html
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from functools import cache
from itertools import batched
from textwrap import dedent

from async_lru import alru_cache
from werkzeug.security import safe_join

from configs import stats_conf
from db import db_q
from db.redis import get_redis
from posts.capcodes import Capcode
from posts.comments import html_comment, html_title
from posts.quotelinks import (
    extract_quotelinks,
    get_quotelink_lookup,
    get_quotelink_lookup_raw
)
from utils.validation import validate_board, validate_boards
from db.base_db import BasePlaceHolderGen


# these comments state the API field names, and descriptions, if applicable
# see the API docs for more info
# https://github.com/4chan/4chan-API/blob/master/pages/Threads.md
selector_columns = (
    'doc_id',
    'num', # `no` - The numeric post ID
    'thread_num', # an archiver construct. The OP post ID.
    'op', # whether or not the post is the thread op (1 == yes, 0 == no)
    'ts_unix', # `time` - UNIX timestamp the post was created
    'ts_expired', # an archiver construct. Could also be `archvied_on` - UNIX timestamp the post was archived
    'preview_orig', # an archiver construct. Thumbnail name, e.g. 1696291733998594s.jpg (an added 's')
    'preview_w', # `tn_w` - Thumbnail image width dimension
    'preview_h', # `tn_h` - Thumbnail image height dimension
    'media_filename', # `filename` - Filename as it appeared on the poster's device, e.g. IMG_3697.jpg
    'media_w', # `w` - Image width dimension
    'media_h', # `h` - Image height dimension
    'media_size', # `fsize` - Size of uploaded file in bytes
    'media_hash', # `md5` - 24 character, packed base64 MD5 hash of file
    'media_orig', # an archiver construct. Full media name, e.g. 1696291733998594.jpg
    'spoiler', # `spoiler` - If the image was spoilered or not
    'deleted', # `filedeleted` - if post had attachment and attachment is deleted
    'capcode', # `capcode` - The capcode identifier for a post
    'name', # `name` - Name user posted with. Defaults to Anonymous
    'trip', # `trip` - the user's tripcode, in format: !tripcode or !!securetripcode
    'title', # `sub` - OP Subject text
    'comment', # `com` - Comment (HTML escaped)
    'sticky', # `sticky`- If the thread is being pinned to the top of the page
    'locked', # `closed` - if the thread is closed to replies
    'poster_hash', # an archiver construct
    'poster_country', # country - Poster's ISO 3166-1 alpha-2 country code, https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
    'exif', # an archiver construct
    'board_shortname', # board acronym
    # 'tim', # `tim` - Unix timestamp + microtime that an image was uploaded. AQ does not use this.
)

# map aliases of cols in board table, back to real board table names
selector_columns_map = {
    'doc_id':           'doc_id',
    'num':              'num',
    'thread_num':       'thread_num',
    'op':               'op',
    'ts_unix' :         'timestamp',
    'ts_expired':       'timestamp_expired',
    'preview_orig':     'preview_orig',
    'preview_w':        'preview_w',
    'preview_h':        'preview_h',
    'media_filename':   'media_filename',
    'media_w':          'media_w',
    'media_h':          'media_h',
    'media_size':       'media_size',
    'media_hash':       'media_hash',
    'media_orig':       'media_orig',
    'spoiler':          'spoiler',
    'deleted':          'deleted',
    'capcode':          'capcode',
    'name':             'name',
    'trip':             'trip',
    'title':            'title',
    'comment':          'comment',
    'sticky':           'sticky',
    'locked':           'locked',
    'poster_hash':      'poster_hash',
    'poster_country':   'poster_country',
    'exif':             'exif',
}


def get_full_media_path(root_path, board, qualifier, media_orig):
    return safe_join(root_path, board, qualifier, media_orig[0:4], media_orig[4:6], media_orig)


def post_has_file(post: dict) -> bool:
    return post.get('tim') and post.get('ext') and post.get('md5')


def get_fs_filename_thumbnail(post: dict) -> str|None:
    if post_has_file(post):
        return f"{post.get('tim')}s.jpg"


def get_fs_filename_full_media(post: dict) -> str|None:
    if post_has_file(post):
        return f"{post.get('tim')}{post.get('ext')}"


def get_asagi_defaults_from_post(post: dict) -> dict:
    return {
            # 'doc_id': post.get('doc_id'), # autoincremented
            'media_id': post.get('media_id', 0),
            'poster_ip': post.get('poster_ip', '0'),
            'num': post.get('num', 0), # this is 'no' in Ritual and had to be changed
            'subnum': post.get('subnum', 0),
            'thread_num': post.get('thread_num'),
            'op': post.get('op', 0),
            'timestamp': post.get('time', 0),
            'timestamp_expired': post.get('archived_on', 0),
            'preview_orig': get_fs_filename_thumbnail(post),
            'preview_w': post.get('preview_w', 0),
            'preview_h': post.get('preview_h', 0),
            'media_filename': post.get('media_filename'),
            'media_w': post.get('media_w', 0),
            'media_h': post.get('media_h', 0),
            'media_size': post.get('media_size', 0),
            'media_hash': post.get('media_hash'),
            'media_orig': get_fs_filename_full_media(post),
            'spoiler': post.get('spoiler', 0),
            'deleted': post.get('filedeleted', 0),
            'capcode': post.get('capcode', 'N'),
            'email': post.get('email'),
            'name': html.unescape(post.get('name')) if post.get('name') else None,
            'trip': post.get('trip'),
            'title': html.unescape(post.get('sub')) if post.get('sub') else None,
            'comment': post.get('com', None),
            'delpass': post.get('delpass'),
            'sticky': post.get('sticky', 0),
            'locked': post.get('closed', 0),
            'poster_hash': post.get('id'),
            'poster_country': post.get('country_name'),
            'exif': json.dumps({'uniqueIps': int(post.get('unique_ips'))}) if post.get('unique_ips') else None,
        }


@cache
def get_selector(board: str) -> str:
    """Remember to update `selector_columns` variable above when you modify these selectors.
    """
    selector = f"""
    select
    doc_id,
    num,
    `{board}`.thread_num,
    op as op,
    timestamp as ts_unix,
    timestamp_expired as ts_expired,
    preview_orig,
    preview_w,
    preview_h,
    media_filename,
    media_w,
    media_h,
    media_size,
    `{board}`.media_hash,
    media_orig,
    spoiler,
    deleted,
    capcode,
    name,
    trip,
    coalesce(title, '') as title,
    coalesce(comment, '') as comment,
    `{board}`.sticky,
    `{board}`.locked,
    poster_hash,
    poster_country,
    exif,
    '{board}' as board_shortname
    """

    return dedent(selector)


# Temporary, needs testing before removing old get_posts_filtered
# TODO: transfer all of this (SqlSearchFilter, validate_and_generate_params, search_posts) to search/providers/sql.py
@dataclass(slots=True)
class SqlSearchFilter:
    fragment: str
    like: bool = False
    placeholder: bool = True
    in_list: bool = False
    fieldname: str|None = None # added due to possible key overlap in `sql_search_filters`


temp_phg = 'жΔж'
sql_search_filters = dict(
    title=SqlSearchFilter(f'title like {temp_phg}', like=True),
    comment=SqlSearchFilter(f'comment like {temp_phg}', like=True),
    media_filename=SqlSearchFilter(f'media_filename like {temp_phg}', like=True),
    media_hash=SqlSearchFilter(f'media_hash = {temp_phg}'),
    date_before=SqlSearchFilter(f'timestamp <= {temp_phg}'),
    date_after=SqlSearchFilter(f'timestamp >= {temp_phg}'),
    has_no_file=SqlSearchFilter("media_filename is null", placeholder=False),
    has_file=SqlSearchFilter("media_filename is not null", placeholder=False),
    is_op=SqlSearchFilter('op = 1', placeholder=False),
    is_not_op=SqlSearchFilter('op = 0', placeholder=False),
    is_deleted=SqlSearchFilter('deleted = 1', placeholder=False),
    is_not_deleted=SqlSearchFilter('deleted = 0', placeholder=False),
    is_sticky=SqlSearchFilter('sticky = 1', placeholder=False),
    is_not_sticky=SqlSearchFilter('sticky = 0', placeholder=False),
    width=SqlSearchFilter(f'media_w >= {temp_phg}'),
    height=SqlSearchFilter(f'media_h >= {temp_phg}'),
    capcode=SqlSearchFilter(f'capcode = {temp_phg}'),
    num=SqlSearchFilter(f'num = {temp_phg}'),
    thread_nums=SqlSearchFilter(None, in_list=True, placeholder=True, fieldname='thread_num'),
)


def validate_and_generate_params(form_data: dict, phg1: BasePlaceHolderGen) -> tuple[str, list]:
    defaults_to_ignore = {
        'width': 0,
        'height': 0,
        'capcode': Capcode.default.value,
    }
    params = []
    where_parts = []
    for field, s_filter in sql_search_filters.items():
        if not (field_val := form_data.get(field)):
            continue

        if (field in defaults_to_ignore) and (field_val == defaults_to_ignore[field]):
            continue

        if s_filter.like:
            field_val = f'%{field_val}%'

        if isinstance(field_val, date) and 1970 <= field_val.year <= 2038:
            field_val = int(datetime.combine(field_val, datetime.min.time()).timestamp())

        if s_filter.in_list and isinstance(field_val, (list, tuple)) and len(field_val) > 0 and s_filter.fieldname:
            s_filter.fragment = f'{s_filter.fieldname} in ({phg1.size(field_val)})'

        if s_filter.placeholder:
            params.extend(field_val) if isinstance(field_val, (list, tuple)) else params.append(field_val)

        where_parts.append(s_filter.fragment.replace(temp_phg, phg1()))

    where_fragment = ' and '.join(where_parts)
    return where_fragment, params


def get_offset(page_num: int, hits_per_page: int) -> str:
    return f'offset {page_num * hits_per_page}' if page_num > 0 and hits_per_page > 0 else ''


def get_facet_where(board: str, where_query: str, form_data: dict, phg: BasePlaceHolderGen) -> str:
    op_title, op_comment = form_data['op_title'], form_data['op_comment']

    pre = ' and' if where_query else ' where '

    if op_title and op_comment:
        return f'''{pre} thread_num in (select thread_num from `{board}` where op = 1 and title like {phg()} and comment like {phg()})'''

    elif op_title and not op_comment:
        return f'''{pre} thread_num in (select thread_num from `{board}` where op = 1 and title like {phg()})'''

    elif not op_title and op_comment:
        return f'''{pre} thread_num in (select thread_num from `{board}` where op = 1 and comment like {phg()})'''

    return ''


def get_like_or_empty(s) -> str:
    return f'%{s}%' if s else ''


def get_facet_params(form_data) -> list[str]:
    op_title, op_comment = get_like_or_empty(form_data['op_title']), get_like_or_empty(form_data['op_comment'])

    if op_title and op_comment:
        return [op_title, op_comment]

    elif op_title and not op_comment:
        return [op_title]

    elif not op_title and op_comment:
        return [op_comment]

    return []


def get_board_2_nums_where(board: str, where_query: str, form_data: dict, phg: BasePlaceHolderGen) -> tuple[str, list]:
    board_2_nums = form_data.get('board_2_nums')

    pre = ' and' if where_query else ' where '

    if board_2_nums and (nums := board_2_nums[board]):
        if not isinstance(nums, set):
            raise TypeError(type(nums), nums)

        return f'''{pre} num in ({phg.size(nums)})''', list(nums)

    return '', []


def get_board_specific_where_clause(board: str, where_query: str, params: list[str], form_data: dict, phg: BasePlaceHolderGen) -> tuple[str, list]:
    """Additional where filters MUST come after `where_query` for Postgresql param counting."""
    where_query += get_min_title_length_where(where_query, form_data)
    where_query += get_min_comment_length_where(where_query, form_data)
    where_query += get_facet_where(board, where_query, form_data, phg)

    board_2_nums_where, board_2_nums_params = get_board_2_nums_where(board, where_query, form_data, phg)
    where_query += board_2_nums_where
    params += board_2_nums_params

    return where_query, params


is_counter_db = 'counter' in db_q.Phg.__slots__
async def get_total_hits(form_data: dict, boards: list[str], max_hits: int, where_query: str, phg1: BasePlaceHolderGen, params: list):
    query_tuple_calls = []
    for board in boards:

        phg2 = db_q.Phg(start=phg1.counter) if hasattr(phg1, 'counter') else db_q.Phg()
        
        where_query, params = get_board_specific_where_clause(board, where_query, params, form_data, phg2)
        params = tuple(params) if params else None

        sql = f"""
        select count(*)
        from `{board}`
        {where_query}
        ;"""

        query_tuple_calls.append(db_q.query_tuple(sql, params=params))

    total_hits_per_board = await asyncio.gather(*query_tuple_calls)

    # what did we find across all board?
    total_hits = min(sum(n[0][0] for n in total_hits_per_board), max_hits)

    return total_hits, total_hits_per_board


def get_min_title_length_where(where_query: str, form_data: dict) -> str:
    min_title_length = form_data.get('min_title_length')
    if min_title_length:
        pre = ' and' if where_query else ' where '
        return f'''{pre} {db_q.length_method}(title) > {int(min_title_length)}'''
    return ''


def get_min_comment_length_where(where_query: str, form_data: dict) -> str:
    min_comment_length = form_data.get('min_comment_length')
    if min_comment_length:
        pre = ' and' if where_query else ' where '
        return f'''{pre} {db_q.length_method}(comment) > {int(min_comment_length)}'''
    return ''


def intersect_form_data(boards: list[str], form_data: dict) -> tuple[list[str], dict]:
    """
    We may avoid queries if form data contradicts itself.
    We perform such checks here.
    """
    board_2_nums: dict[str, set[int]] = form_data.get('board_2_nums', dict())

    # boards intersection
    if board_2_nums:
        boards = [b for b in boards if b in board_2_nums]

        for board in list(board_2_nums):
            if board not in boards:
                board_2_nums.pop(board)

        # just assign this and don't worry about possible states
        form_data['board_2_nums'] = board_2_nums

        if not boards or not board_2_nums:
            return None, None

    # consolidate nums - no more 'num' field in form_data
    if form_data.get('num') and board_2_nums:
        num = form_data.pop('num')
        for board in boards:
            nums = board_2_nums[board]
            if not isinstance(nums, set):
                raise TypeError(type(nums), nums)
            nums.add(num)

    return boards, form_data


async def search_posts(form_data: dict, max_hits: int) -> tuple[list[dict], int]:
    boards: list[str] | str = form_data.pop('boards')

    if not boards:
        return [], 0

    if boards and isinstance(boards, str):
        boards = [boards]

    if not isinstance(boards, list):
        raise TypeError(boards)

    boards, form_data = intersect_form_data(boards, form_data)
    if (not boards) or (form_data is None):
        return [], 0

    validate_boards(boards)

    # some extra validation
    order_by: str = dict(asc='asc', desc='desc')[form_data['order_by']]
    hits_per_page: int = int(form_data['hits_per_page'])
    page_num: int = int(form_data['page'])

    if max_hits and (page_num * hits_per_page > max_hits):
        page_num = int(max_hits / hits_per_page)

    phg1 = db_q.Phg()
    where_filters, params = validate_and_generate_params(form_data, phg1)
    where_query = f'where {where_filters}' if where_filters else ''

    offset = get_offset(page_num - 1, hits_per_page)

    params += get_facet_params(form_data)

    total_hits, total_hits_per_board = await get_total_hits(form_data, boards, max_hits, where_query, phg1, params.copy())

    if not total_hits:
        return [], 0

    # we only want <hits_per_page> in each search page's results
    hits_per_board_to_query: dict[str, int] = {}

    prev_page_hits = 0

    hits_for_this_page = 0
    for i, board in enumerate(boards):
        board_hits: int = total_hits_per_board[i][0][0]
        if not board_hits:
            continue

        # offset
        recs = board_hits - ((page_num - 1) * hits_per_page)
        if page_num > 1 and hits_per_page and (recs < prev_page_hits):
            prev_page_hits += board_hits
            continue
        prev_page_hits += board_hits

        if not hits_per_board_to_query or (hits_for_this_page < hits_per_page):
            hits_per_board_to_query[board] = min(hits_per_page - hits_for_this_page, board_hits)
            hits_for_this_page += hits_per_board_to_query[board]
        else:
            break

    if not hits_for_this_page or not hits_per_board_to_query:
        return [], 0

    calls = []
    for board in hits_per_board_to_query.keys():
        phg2 = db_q.Phg(start=phg1.counter) if hasattr(phg1, 'counter') else db_q.Phg()

        where_query, params = get_board_specific_where_clause(board, where_query, params, form_data, phg2)
        params = tuple(params) if params else None

        sql = f"""
            {get_selector(board)}
            from `{board}`
            {where_query}
            order by ts_unix {order_by}
            limit {hits_per_board_to_query[board]}
            {offset}
        """
    
        calls.append(db_q.query_dict(sql, params=params))

    board_posts = await asyncio.gather(*calls)

    if not board_posts:
        return [], 0

    posts = []

    # board_posts = [[post, post], ...] for each board, there is 1 sub-list
    for board_post in board_posts:
        posts.extend(board_post)

    board_quotelinks = await get_board_2_ql_lookup(posts)

    for post in posts:
        post['quotelinks'] = board_quotelinks.get(post['board_shortname'], {}).get(post['num'], set())

    return posts, total_hits


def get_qls_and_posts(rows: list[dict], gather_qls: bool=True) -> tuple[dict, list]:
    post_2_quotelinks = defaultdict(list)
    posts = []
    for row in rows:
        row['comment'] = html_comment(row['comment'], row['thread_num'], row['board_shortname'])

        if gather_qls:
            row_quotelinks = extract_quotelinks(row['comment'])
            for row_quotelink in row_quotelinks:
                post_2_quotelinks[row_quotelink].append(row['num'])

        if row['title']:
            row['title'] = html.escape(row['title'])

        posts.append(row)

    return post_2_quotelinks, posts


async def get_board_2_ql_lookup(posts: list[dict]) -> dict[str, dict[int, list[int]]]:
    board_thread_nums = defaultdict(set)
    for post in posts:
        board_thread_nums[post['board_shortname']].add(post['thread_num'])

    board_thread_nums = [(board, tuple(thread_nums)) for board, thread_nums in board_thread_nums.items()]

    board_qls = await asyncio.gather(*(
        get_board_thread_quotelinks(board, thread_nums)
        for board, thread_nums in board_thread_nums
    ))

    return {board: ql_lookup for (board, _thread_nums), ql_lookup in zip(board_thread_nums, board_qls)}


async def get_board_thread_quotelinks(board: str, thread_nums: tuple[int]):
    sql = f'''
        select num, comment
        from `{board}`
        where comment is not null
        and thread_num in ({db_q.Phg().size(thread_nums)})
    '''
    rows = await db_q.query_dict(sql, params=thread_nums)
    return get_quotelink_lookup(rows)


async def get_op_thread_count(board: str) -> int:
    rows = await db_q.query_tuple(f'select count(*) from `{board}_threads`;')
    return rows[0][0]


square_re = re.compile(r'.*\[(spoiler|code|banned)\].*\[/(spoiler|code|banned)\].*')
spoiler_re = re.compile(r'\[spoiler\](.*?)\[/spoiler\]', re.DOTALL)  # with re.DOTALL, the dot matches any character, including newline characters.
spoiler_sub = r'<span class="spoiler">\1</span>'
code_re = re.compile(r'\[code\](.*?)\[/code\]', re.DOTALL)  # ? makes the (.*) non-greedy
code_sub = r'<code>\1</code>'
banned_re = re.compile(r'\[banned\](.*?)\[/banned\]', re.DOTALL)
banned_sub = r'<span class="banned">\1</span>'


def substitute_square_brackets(text):
    if square_re.fullmatch(text):
        text = spoiler_re.sub(spoiler_sub, text)
        text = code_re.sub(code_sub, text)
        text = banned_re.sub(banned_sub, text)
    return text


async def generate_index(board: str, page_num: int=1):
    """
    - Generates the board index.
    - The index shows the OP and its 3 latest comments, if any.
    - The returned titles and comments are html escaped.

    Returns the dict:

    ```
    {'threads': [
        {'posts': [{OP1}, {reply1}, {reply2}, ...]},
        {'posts': [{OP2}, {reply1}, {reply2}, ...]},
    ]}
    ```

    OPs have these extra fields added to them:
        - nreplies: int
        - nimages: int
        # - omitted_posts: int (to be implemented)
        # - omitted_images: int (to be implemented)
    """
    index_post_count = 10

    sql = f'''
        select
            thread_num,
            nreplies,
            nimages
        from `{board}_threads`
        order by time_op desc
        limit {index_post_count}
        {get_offset(page_num - 1, index_post_count)}
    '''

    if not (threads := await db_q.query_dict(sql)):
        return {'threads': []}, {}

    phg_size = db_q.Phg().size(threads)

    op_query = f'''
    {get_selector(board)}
    from `{board}`
    where
        op = 1
        and thread_num in ({phg_size})
    '''

    replies_query = f'''
    with latest_replies as (
        select
            num as reply_num,
            row_number() over (
                partition by `{board}`.thread_num order by `{board}`.num desc
            ) as reply_number
        from `{board}`
        where
            op = 0
            and thread_num in ({phg_size})
    )
    {get_selector(board)}
    from latest_replies
    left join `{board}` on
        latest_replies.reply_num = `{board}`.num
    where latest_replies.reply_number <= 3
    '''

    thread_nums = tuple(t['thread_num'] for t in threads)
    thread_nums_d = {t['thread_num']:t for t in threads}

    ops, replies, ql_lookup = await asyncio.gather(
        db_q.query_dict(op_query, params=thread_nums),
        db_q.query_dict(replies_query, params=thread_nums),
        get_board_thread_quotelinks(board, thread_nums)
    )

    for reply in replies:
        reply['title'] = html_title(reply['title'])
        reply['comment'] = html_comment(reply['comment'], reply['thread_num'], board)

    thread_posts = defaultdict(list)
    for op in ops:
        thread_num = op['num']
        op['title'] = html_title(op['title'])
        op['comment'] = html_comment(op['comment'], thread_num, board)

        op.update(thread_nums_d[thread_num])
        thread_posts[thread_num].append(op)

    for reply in replies:
        thread_posts[reply['thread_num']].append(reply)

    threads = {
        'threads': [
            {'posts': thread_posts[thread['thread_num']]}
            for thread in threads
        ]
    }
    return threads, ql_lookup


def get_counts_from_posts(posts: list[dict]) -> tuple[int]:
    """Returns (nreplies, nimages)"""
    nreplies = len(posts) - 1
    nimages = sum(1 for p in posts if p['media_filename'])
    return nreplies, nimages


async def generate_catalog(board: str, page_num: int=1):
    """
    - Generates the catalog structure.
    - Returns html escaped titles and comments.
    - Does not parse comments with `html_comment()`
    """
    catalog_post_count = 150

    threads_query = f'''
        select
            thread_num,
            nreplies,
            nimages
        from `{board}_threads`
        order by time_op desc
        limit {catalog_post_count}
        {get_offset(page_num - 1, catalog_post_count)}
    '''

    if not (rows := await db_q.query_tuple(threads_query)):
        return []

    threads = {row[0]: row[1:] for row in rows}

    posts_query = f'''
        {get_selector(board)}
    from `{board}`
    where op = 1
    and thread_num in ({db_q.Phg().size(threads)})
    order by thread_num desc
    '''
    posts = await db_q.query_dict(posts_query, params=tuple(threads.keys()))
    if not posts:
        return []

    for post in posts:
        post['title'] = html_title(post['title'])
        post['comment'] = html_title(post['comment'])

    batch_size = 15
    return [
        {
            "page": i,
            'threads': [{
                    **post,
                    'quotelinks': [],
                    'nreplies': (thread:=threads[post['num']])[0],
                    'nimages': thread[1]
                }
                for post in batch
            ]
        }
        for i, batch in
        enumerate(batched(posts, batch_size))
    ]


async def generate_thread(board: str, thread_num: int) -> tuple[dict]:
    """Generates a thread.

    The post tuple is tuple[1]:
    ```
        {'posts': [{...}, {...}, {...}, ...]}, 
    ```

    OPs have these extra fields added to them compared to comments:
        - nreplies: int
        - nimages: int
    """

    thread_query = f'''
        select
            nreplies,
            nimages
        from `{board}_threads`
        where thread_num = {db_q.Phg()()}
    ;'''

    posts_query = f'''
        {get_selector(board)}
        from `{board}`
        where thread_num = {db_q.Phg()()}
        order by num asc
    ;'''
    threads_details, posts = await asyncio.gather(
        db_q.query_dict(thread_query, params=(thread_num,)),
        db_q.query_dict(posts_query, params=(thread_num,)),
    )
    if not threads_details or not posts:
        return {}, {'posts': []}

    # post_2_quotelinks, posts = get_qls_and_posts(posts)
    post_2_quotelinks = get_quotelink_lookup_raw(posts)
    for post in posts:
        if not (comment := post['comment']):
            continue

        post['title'] = html_title(post['title'])
        post['comment'] = html_comment(comment, thread_num, board)

    posts[0].update(threads_details[0])
    results = {'posts': posts}

    return post_2_quotelinks, results


async def generate_post(board: str, post_id: int) -> tuple[dict]:
    """Returns {thread_num: 123, comment: 'hello', ...} with quotelinks"""

    sql = f"""
        {get_selector(board)}
        from `{board}`
        where num = {db_q.Phg()()}
    ;"""
    posts = await db_q.query_dict(sql, params=(post_id,))

    if not posts:
        return None, None

    # escapes title and comment for us
    post_2_quotelinks, posts = get_qls_and_posts(posts)
    return post_2_quotelinks, posts[0]


async def get_post(board: str, post_id: int) -> dict:
    """Returns {thread_num: 123, comment: 'hello', ...} without quotelinks"""

    sql = f"""
        {get_selector(board)}
        from `{board}`
        where num = {db_q.Phg()()}
    ;"""
    posts = await db_q.query_dict(sql, params=(post_id,))

    if not posts:
        return dict()

    return posts[0]


async def get_post_with_doc_id(board: str, post_id: int) -> dict:
    """Returns {thread_num: 123, comment: 'hello', ...} without quotelinks"""

    sql = f"""
        {get_selector(board)}
        from `{board}`
        where num = {db_q.Phg()()}
    ;"""
    posts = await db_q.query_dict(sql, params=(post_id,))

    if not posts:
        return dict()

    return posts[0]


async def move_post_to_delete_table(post: dict) -> str:
    """Insert post into `<board>_deleted` table first. If we fail at that, do nothing.

    Returns a flash message.
    """
    board = post['board_shortname']

    post_for_insert = {selector_columns_map[k]: v for k, v in post.items() if k in selector_columns_map}
    post_for_insert = post_for_insert | {'media_id': 0, 'poster_ip': '0', 'subnum': 0}
    del post_for_insert['doc_id']

    phg = db_q.Phg()

    sql_cols = ','.join(post_for_insert)
    sql_values = phg.size(post_for_insert)
    sql = f"""insert into `{board}_deleted` ({sql_cols}) values ({sql_values});"""

    values = list(post_for_insert.values())

    msg = ''

    try:
        await db_q.query_dict(sql, params=values, commit=True)
        msg += f' Post transfered to `{board}_deleted`.'
    except:
        msg += f' An error arose when inserting the post into the deleted table. Are you sure `{board}_deleted` exists?'

    sql = f"""delete from `{board}` where num = {db_q.Phg()()};"""
    await db_q.query_dict(sql, params=(post['num'],), commit=True)

    msg += f' Post deleted from `{board}` table.'

    return msg


async def get_deleted_ops_by_board(board: str) -> list[int]:
    """Returns op post nums marked as deleted by 4chan staff."""
    
    sql = f"""select num from `{board}` where deleted = 1 and op = 1"""
    rows = await db_q.query_tuple(sql)
    if not rows:
        return []
    return [(row[0], row[1]) for row in rows]


async def get_deleted_non_ops_by_board(board: str) -> list[int]:
    """Returns non-op post nums marked as deleted by 4chan staff."""
    
    sql = f"""select num from `{board}` where deleted = 1 and op = 0;"""
    rows = await db_q.query_tuple(sql)
    if not rows:
        return []
    return [(row[0], row[1]) for row in rows]


async def get_deleted_numops_by_board(board: str) -> list[tuple[int]]:
    """Returns all nums marked as deleted by 4chan staff in the format [(num, op), ...]"""

    sql = f"""select num, op from `{board}` where deleted = 1;"""
    rows = await db_q.query_tuple(sql)
    if not rows:
        return []
    return [(row[0], row[1]) for row in rows]


async def get_numops_by_board_and_regex(board: str, pattern: str) -> list[tuple[int]]:
    sql = f"""select num, op from `{board}` where comment is not null and comment regexp {db_q.Phg()()};"""
    
    rows = await db_q.query_tuple(sql, params=(pattern,))
    if not rows:
        return []
    return [(row[0], row[1]) for row in rows]


async def is_post_op(board: str, num: int) -> bool:
    
    sql = f"""select num, op from `{board}` where num = {db_q.Phg()()}"""
    rows = await db_q.query_tuple(sql, params=[num])
    if not rows:
        return False
    return rows[0][1]


@alru_cache(ttl=60*60*24)
async def _get_post_counts_per_month_by_board(board: str):
    validate_board(board)
    rows = await db_q.query_dict(
        f"""
        select
            '{board}' as board,
            strftime('%Y-%m', datetime(timestamp, 'unixepoch')) AS year_month,
            min(num) as min_post_num,
            max(num) as max_post_num,
            count(*) as post_count,
            round(count(*) * 100.0 / (max(num) - min(num)), 1) as fraction
        from `{board}`
        group by 1, 2
        order by 1, 2
        ;"""
    )
    for row in rows:
        row['fraction'] = min(row['fraction'], 1.0) if row['fraction'] else None
    return rows


async def get_post_counts_per_month_by_board(board: str) -> str:
    """Returns json formatted string.
    """
    if stats_conf['redis']:
        r = get_redis(stats_conf['redis_db'])

        key = f'post_counts_{board}'
        post_counts = await r.get(key)
        if post_counts:
            return post_counts # do not loads(), cache dumps()

        post_counts = await _get_post_counts_per_month_by_board(board)
        post_counts = json.dumps(post_counts)
        if post_counts:
            await r.set(key, post_counts)
        return post_counts

    post_counts = await _get_post_counts_per_month_by_board(board)
    return json.dumps(post_counts)


async def get_latest_ops_as_catalog(boards: list[str]):
    latest_ops = await asyncio.gather(*(
        db_q.query_dict(f"""
            {get_selector(board)}
            FROM `{board}`
            WHERE op = 1
            ORDER BY num DESC
            LIMIT 5;
        """)
        for board in boards
    ))
    return [{
        "page": 1,
        'threads': [
            thread[0] | dict(nreplies='?', nimages='?', quotelinks={})
            for thread in latest_ops
            if thread
        ],
    }]


async def get_board_2_nums_from_board_2_filenames(board_2_filenames: dict[str, list[str]]) -> dict[str, tuple[int]]:
    sql_calls = [
        db_q.query_tuple(f"""select num from `{board}` where media_orig in ({db_q.Phg().size(filenames)})""", params=filenames)
        for board, filenames in board_2_filenames.items()
        if filenames
    ]
    rows = await asyncio.gather(*sql_calls) if sql_calls else None

    if not rows and not any(rows):
        return {}

    board_2_nums = dict()
    for board, row in zip(board_2_filenames, rows):
        if row:
            board_2_nums[board] = row[0]
    return board_2_nums


async def get_pk_and_media_orig(board: str, page: int, per_page: int):
    sql = f'select doc_id, media_orig from `{board}` where media_orig is not null order by doc_id limit {int(per_page)} offset {int(page)}'
    rows = await db_q.query_tuple(sql)
    return rows


async def get_pk_and_media_orig_count(board: str) -> int:
    sql = f'select count(*) from `{board}` where media_orig is not null'
    rows = await db_q.query_tuple(sql)
    return int(rows[0][0])
