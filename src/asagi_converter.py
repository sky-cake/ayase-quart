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

from db import db_q
from posts.capcodes import Capcode
from posts.comments import html_comment
from posts.quotelinks import get_quotelink_lookup, get_quotelink_lookup_raw
from search.highlighting import highlight_search_results

# these comments state the API field names, and descriptions, if applicable
# see the API docs for more info
# https://github.com/4chan/4chan-API/blob/master/pages/Threads.md
selector_columns = (
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
    'op_num', # thread_num
    'board_shortname', # board acronym
    # 'tim', # `tim` - Unix timestamp + microtime that an image was uploaded. AQ does not use this.
)

# map aliases of cols in board table, back to real board table names
selector_columns_map = {
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
    num as num,
    {board}.thread_num as thread_num,
    op as op,
    timestamp as ts_unix,
    timestamp_expired as ts_expired,
    preview_orig as preview_orig,
    preview_w as preview_w,
    preview_h as preview_h,
    media_filename as media_filename,
    media_w as media_w,
    media_h as media_h,
    media_size as media_size,
    {board}.media_hash as media_hash,
    media_orig as media_orig,
    spoiler as spoiler,
    deleted as deleted,
    capcode as capcode,
    name as name,
    trip as trip,
    coalesce(title, '') as title,
    comment as comment,
    {board}.sticky as sticky,
    {board}.locked as locked,
    poster_hash as poster_hash,
    poster_country as poster_country,
    exif as exif,
    case when op=1 then num else {board}.thread_num end as op_num,
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

phg = db_q.phg()
sql_search_filters = dict(
    title=SqlSearchFilter(f'title like {phg}', like=True),
    comment=SqlSearchFilter(f'comment like {phg}', like=True),
    media_filename=SqlSearchFilter(f'media_filename like {phg}', like=True),
    media_hash=SqlSearchFilter(f'media_hash = {phg}'),
    num=SqlSearchFilter(f'num = {phg}'),
    date_before=SqlSearchFilter(f'timestamp <= {phg}'),
    date_after=SqlSearchFilter(f'timestamp >= {phg}'),
    has_no_file=SqlSearchFilter("(media_filename is null or media_filename = '')", placeholder=False),
    has_file=SqlSearchFilter("media_filename is not null and media_filename != ''", placeholder=False),
    is_op=SqlSearchFilter('op = 1', placeholder=False),
    is_not_op=SqlSearchFilter('op = 0', placeholder=False),
    is_deleted=SqlSearchFilter('deleted = 1', placeholder=False),
    is_not_deleted=SqlSearchFilter('deleted = 0', placeholder=False),
    is_sticky=SqlSearchFilter('sticky = 1', placeholder=False),
    is_not_sticky=SqlSearchFilter('sticky = 0', placeholder=False),
    width=SqlSearchFilter(f'media_w = {phg}'),
    height=SqlSearchFilter(f'media_h = {phg}'),
    capcode=SqlSearchFilter(f'capcode = {phg}'),
    thread_nums=SqlSearchFilter(None, in_list=True, placeholder=True, fieldname='thread_num'),
)

def validate_and_generate_params(form_data: dict):
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

        if s_filter.in_list and isinstance(field_val, list) and len(field_val) > 0 and s_filter.fieldname:
            s_filter.fragment = f'{s_filter.fieldname} in ({db_q.phg.size(field_val)})'

        if s_filter.placeholder:
            params.extend(field_val) if isinstance(field_val, list) else params.append(field_val)

        where_parts.append(s_filter.fragment)

    where_fragment = ' and '.join(where_parts)
    params = tuple(params)
    return where_fragment, params


def get_offset(page_num: int, page_size: int) -> str:
    return f'offset {page_num * page_size}' if page_num > 0 and page_size > 0 else ''


async def search_posts(form_data: dict) -> tuple[list[dict], int]:
    """Returns posts that not been restored with `restore_comment()`."""

    boards = form_data['boards']
    hits_per_page = form_data['hits_per_page']
    order_by = form_data['order_by']
    page_num = form_data['page']

    where_filters, params = validate_and_generate_params(form_data)
    where_query = f'where {where_filters}' if where_filters else ''

    board_posts = await asyncio.gather(*(
        db_q.query_dict(f"""
            {get_selector(board)}
            from {board}
            {where_query}
            order by ts_unix {order_by}
            limit {hits_per_page}
            {get_offset(page_num - 1, hits_per_page)}
            """, params=params
        ) for board in boards)
    )

    total_hits = await asyncio.gather(*(
        db_q.query_tuple(f"""select count(*) from {board} {where_query}""", params=params)
        for board in boards
    ))
    total_hits = sum(n[0][0] for n in total_hits)

    posts = []
    for board_post in board_posts:
        posts.extend(board_post)

    if not posts:
        return [], total_hits  # posts, total_hits

    board_quotelinks = await get_board_2_ql_lookup(posts)

    for post in posts:
        board = post['board_shortname']
        post['quotelinks'] = board_quotelinks.get(board, {}).get(post['num'], set())

    return posts, total_hits


async def search_posts_get_thread_nums(form_data: dict) -> dict:
    """Returns {board_shortname: thread_nums} mappings.
    Used for faceted search.
    """

    boards = form_data['boards']
    hits_per_page = form_data['hits_per_page']
    page_num = form_data['page']
    form_d = {'is_op': 1, 'title': form_data['op_title'], 'comment': form_data['op_comment']}

    where_filters, params = validate_and_generate_params(form_d)
    where_query = f'where {where_filters}' if where_filters else ''

    board_posts = await asyncio.gather(*(
        db_q.query_dict(f"""
            {f"select '{board}' as board_shortname, num as thread_num"}
            from {board}
            {where_query}
            limit {hits_per_page}
            {get_offset(page_num - 1, hits_per_page)}
            """, params=params
        ) for board in boards)
    )

    posts = []
    for board_post in board_posts:
        posts.extend(board_post)

    if not posts:
        return {}

    d = defaultdict(list)
    for p in posts:
        d[p.board_shortname].append(p.thread_num)
    return d


def get_qls_and_posts(rows: list[dict], gather_qls: bool=True) -> tuple[dict, list]:
    post_2_quotelinks = defaultdict(list)
    posts = []
    for row in rows:
        row_quotelinks, row['comment'] = restore_comment(row['thread_num'], row['comment'], row['board_shortname'])

        if gather_qls:
            for row_quotelink in row_quotelinks:
                post_2_quotelinks[row_quotelink].append(row['num'])

        if row['title']:
            row['title'] = html.escape(row['title'])

        posts.append(row)

    return post_2_quotelinks, posts


async def get_board_2_ql_lookup(posts: list[dict]) -> dict[str, dict[int, list[int]]]:
    board_op_nums = defaultdict(set)
    for post in posts:
        board_op_nums[post['board_shortname']].add(post['op_num'])

    board_op_nums = [(board, tuple(op_nums)) for board, op_nums in board_op_nums.items()]

    board_qls = await asyncio.gather(*(
        get_board_thread_quotelinks(board, op_nums)
        for board, op_nums in board_op_nums
    ))

    return {board: ql_lookup for (board, _op_nums), ql_lookup in zip(board_op_nums, board_qls)}


async def get_board_thread_quotelinks(board: str, thread_nums: tuple[int]):
    query = f'''
        select num, comment
        from {board}
        where comment is not null
        and thread_num in ({db_q.phg.size(thread_nums)})
    '''
    rows = await db_q.query_dict(query, params=thread_nums)
    return get_quotelink_lookup(rows)


async def get_op_thread_count(board: str) -> int:
    rows = await db_q.query_tuple(f'select count(*) from {board}_threads;')
    return rows[0][0]


square_re = re.compile(r'.*\[(spoiler|code|banned)\].*\[/(spoiler|code|banned)\].*')
spoiler_re = re.compile(r'\[spoiler\](.*?)\[/spoiler\]', re.DOTALL)  # with re.DOTALL, the dot matches any character, including newline characters.
spoiler_sub = r'<span class="spoiler">\1</span>'
code_re = re.compile(r'\[code\](.*?)\[/code\]', re.DOTALL)  # ? makes the (.*) non-greedy
code_sub = r'<code><pre>\1</pre></code>'
banned_re = re.compile(r'\[banned\](.*?)\[/banned\]', re.DOTALL)
banned_sub = r'<span class="banned">\1</span>'


def substitute_square_brackets(text):
    if square_re.fullmatch(text):
        text = spoiler_re.sub(spoiler_sub, text)
        text = code_re.sub(code_sub, text)
        text = banned_re.sub(banned_sub, text)
    return text


def restore_comment(op_num: int, comment: str, board_shortname: str, hl_search_term: str=None):
    """
    Re-convert asagi stripped comment into clean html.
    Also create a dictionary with keys containing the num, which maps to a tuple containing the posts it links to.

    Returns a string (the processed comment) and a list of quotelinks in
    the post.

    greentext: a line that begins with a single ">" and ends with a '\n'
    redirect: a line that begins with a single ">>", has a thread number afterward that exists in the current thread or another thread (may be inline)

    >> (show OP)
    >>>/g/ (board redirect)
    >>>/g/<num> (board post redirect)
    """

    quotelinks = []

    GT = '&gt;'
    GTGT = "&gt;&gt;"

    if comment is None:
        return [], ''

    lines = html.escape(comment).split("\n")
    hl_search_term = html.escape(hl_search_term) if hl_search_term else None
    for i, line in enumerate(lines):
        # >green text
        if GT == line[:4] and GT != line[4:8]:
            lines[i] = f"""<span class="quote">{highlight_search_results(line, hl_search_term)}</span>"""
            continue

        # >>123456789
        elif GTGT in line:
            tokens = line.split(" ")

            for j, token in enumerate(tokens):
                if token[:8] == GTGT and token[8:].isdigit():
                    quotelinks.append(int(token[8:]))
                    tokens[j] = f"""<a href="/{board_shortname}/thread/{op_num}#p{token[8:]}" class="quotelink" data-board_shortname="{board_shortname}">{token}</a>"""

            lines[i] = " ".join(tokens)

        else:
            lines[i] = highlight_search_results(line, hl_search_term) # will not highlight matches if line has a quotelink for performance

    lines = "</br>".join(lines)
    lines = substitute_square_brackets(lines)

    return quotelinks, lines


async def generate_index(board: str, page_num: int=1):
    """Generates the board index. The index shows the OP and its 3 latest comments, if any.

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

    threads_q = f'''
        select
            thread_num,
            nreplies,
            nimages
        from {board}_threads
        order by time_op desc
        limit {index_post_count}
        {get_offset(page_num - 1, index_post_count)}
    '''
    if not (threads := await db_q.query_dict(threads_q)):
        return {'threads': []}, {}

    thread_phs = db_q.phg.size(threads)

    op_query = f'''
    {get_selector(board)}
    from {board}
    where
        op = 1
        and thread_num in ({thread_phs})
    '''

    replies_query = f'''
    with latest_replies as (
        select
            num as reply_num,
            row_number() over (
                partition by {board}.thread_num order by {board}.num desc
            ) as reply_number
        from {board}
        where
            op = 0
            and thread_num in ({thread_phs})
    )
    {get_selector(board)}
    from latest_replies
    left join {board} on
        latest_replies.reply_num = {board}.num
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
        _, reply['comment'] = restore_comment(reply['op_num'], reply['comment'], board)

    thread_posts = defaultdict(list)
    for op in ops:
        op_num = op['num']
        _, op['comment'] = restore_comment(op_num, op['comment'], board)
        op.update(thread_nums_d[op_num])
        thread_posts[op_num].append(op)
    for reply in replies:
        thread_posts[reply['op_num']].append(reply)

    threads = {
        'threads': [
            {'posts': thread_posts[thread['thread_num']]}
            for thread in threads
        ]
    }
    return threads, ql_lookup


async def generate_catalog(board: str, page_num: int=1):
    """Generates the catalog structure"""
    catalog_post_count = 150

    threads_q = f'''
        select
            thread_num,
            nreplies,
            nimages
        from {board}_threads
        order by time_op desc
        limit {catalog_post_count}
        {get_offset(page_num - 1, catalog_post_count)}
    '''
    if not (rows := await db_q.query_tuple(threads_q)):
        return []

    threads = {row[0]: row[1:] for row in rows}

    posts_q = f'''
        {get_selector(board)}
    from {board}
    where op = 1
    and thread_num in ({db_q.phg.size(threads)})
    order by thread_num desc
    '''
    rows = await db_q.query_dict(posts_q, params=tuple(threads.keys()))

    batch_size = 15
    return [
        {
            "page": i,
            'threads': [{
                    **row,
                    'quotelinks': [],
                    'nreplies': (thread:=threads[row['num']])[0],
                    'nimages': thread[1]
                }
                for row in batch
            ]
        }
        for i, batch in
        enumerate(batched(rows, batch_size))
    ]


async def generate_thread(board: str, thread_num: int) -> tuple[dict]:
    """Generates a thread.

    Returns the dict:
    ```
        {'posts': [{...}, {...}, {...}, ...]}
    ```

    OPs have these extra fields added to them compared to comments:
        - nreplies: int
        - nimages: int
    """
    phg = db_q.phg()
    thread_query = f'''
        select
            nreplies,
            nimages
        from {board}_threads
        where thread_num = {phg}
    ;'''
    posts_query = f'''
        {get_selector(board)}
        from {board}
        where thread_num = {phg}
        order by num asc
    ;'''
    threads_details, posts = await asyncio.gather(
        db_q.query_dict(thread_query, params=(thread_num,)),
        db_q.query_dict(posts_query, params=(thread_num,)),
    )
    if not threads_details:
        return {}, {'posts': []}

    # post_2_quotelinks, posts = get_qls_and_posts(posts)
    post_2_quotelinks = get_quotelink_lookup_raw(posts)
    for post in posts:
        if not (comment := post['comment']):
            continue
        post['comment'] = html_comment(comment, thread_num, board)
    
    posts[0].update(threads_details[0])
    results = {'posts': posts}
    
    return post_2_quotelinks, results


async def generate_post(board: str, post_id: int) -> tuple[dict]:
    """Returns {thread_num: 123, comment: 'hello', ...} with quotelinks"""
    sql = f"""
        {get_selector(board)}
        from {board}
        where num = {db_q.phg()}
    ;"""
    posts = await db_q.query_dict(sql, params=(post_id,))

    if not posts:
        return None, None

    post_2_quotelinks, posts = get_qls_and_posts(posts)
    return post_2_quotelinks, posts[0]


async def get_post(board: str, post_id: int) -> dict:
    """Returns {thread_num: 123, comment: 'hello', ...} wihtout quotelinks"""
    sql = f"""
        {get_selector(board)}
        from {board}
        where num = {db_q.phg()}
    ;"""
    posts = await db_q.query_dict(sql, params=(post_id,))

    if not posts:
        return dict()

    return posts[0]


async def move_post_to_delete_table(board: str, post_id: int) -> tuple[dict, str]:
    """Insert post into `<board>_deleted` table first. If we fail at that, do nothing.
    
    Returns the post dict, and a flash message.
    """
    post = await get_post(board, post_id)
    if not post:
        return (post, 'Did not locate post in asagi database. Did nothing as a result.')

    post = {selector_columns_map[k]: v for k, v in post.items() if k in selector_columns_map}
    post = post | {'media_id': 0, 'poster_ip': '0', 'subnum': 0}

    phg = db_q.phg()
    sql_cols = ', '.join(post)
    sql_conflict = ', '.join([f'{col}={phg}' for col in post])

    sql = f"""insert into `{board}_deleted` ({sql_cols}) values ({db_q.phg.size(post)}) on conflict(`num`) do update set {sql_conflict} returning `num`;"""
    values = list(post.values())
    parameters = values + values
    num = await db_q.query_dict(sql, params=parameters, commit=True)

    if not num:
        return (post, 'Did not transfer post to asagi\'s delete table. It is still in the board table.')

    sql = f"""
        delete
        from {board}
        where num = {phg}
    ;"""
    await db_q.query_dict(sql, params=(post_id,), commit=True)

    return (post, 'Post transfered to asagi\'s delete table. It is no longer in the board table.')


async def get_deleted_ops_by_board(board: str) -> list[int]:
    """Returns op post nums marked as deleted by 4chan staff."""
    sql = f"""select num from {board} where deleted = 1 and op = 1"""
    return [row[0] for row in (await db_q.query_tuple(sql))]


async def get_deleted_non_ops_by_board(board: str) -> list[int]:
    """Returns non-op post nums marked as deleted by 4chan staff."""
    sql = f"""select num from {board} where deleted = 1 and op = 0;"""
    return [row[0] for row in (await db_q.query_tuple(sql))]


async def get_deleted_numops_by_board(board: str) -> list[tuple[int]]:
    """Returns all nums marked as deleted by 4chan staff in the format [(num, op), ...]"""
    sql = f"""select num, op from {board} where deleted = 1;"""
    return [(row[0], row[1]) for row in (await db_q.query_tuple(sql))]


async def get_numops_by_board_and_regex(board: str, pattern: str) -> list[tuple[int]]:
    sql = f"""select num, op from {board} where comment regexp {db_q.phg()};"""
    return [(row[0], row[1]) for row in (await db_q.query_tuple(sql, params=(pattern,)))]


async def is_post_op(board_shortname: str, num: int) -> bool:
    sql = f"""select num, op from {board_shortname} where num = {db_q.phg()}"""
    rows = await db_q.query_tuple(sql, params=[num])
    if not rows:
        return False
    return rows[0][1]
