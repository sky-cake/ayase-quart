import html
import re
from collections import defaultdict
from functools import cache
from textwrap import dedent
from itertools import batched
import asyncio
from datetime import date, datetime

from werkzeug.exceptions import BadRequest

from posts.capcodes import Capcode
from posts.quotelinks import get_quotelink_lookup
from search.highlighting import html_highlight
from db import query_tuple, query_dict, Phg

# these comments state the API field names, and descriptions, if applicable
# see the API docs for more info
# https://github.com/4chan/4chan-API/blob/master/pages/Threads.md
selector_columns = (
    'thread_num', # an archiver construct. The OP post ID.
    'num', # `no` - The numeric post ID
    'board_shortname', # board acronym
    'ts_expired', # an archiver construct. Could also be `archvied_on` - UNIX timestamp the post was archived
    'name', # `name` - Name user posted with. Defaults to Anonymous
    'sticky', # `sticky`- If the thread is being pinned to the top of the page
    'title', # `sub` - OP Subject text
    'media_w', # `w` - Image width dimension
    'media_h', # `h` - Image height dimension
    'preview_w', # `tn_w` - Thumbnail image width dimension 	
    'preview_h', # `tn_h` - Thumbnail image height dimension
    'ts_unix', # `time` - UNIX timestamp the post was created
    'preview_orig', # an archiver construct. Thumbnail name, e.g. 1696291733998594s.jpg (an added 's')
    'media_orig', # an archiver construct. Full media name, e.g. 1696291733998594.jpg
    'media_hash', # `md5` - 24 character, packed base64 MD5 hash of file
    'media_size', # `fsize` - Size of uploaded file in bytes
    'media_filename', # `filename` - Filename as it appeared on the poster's device, e.g. IMG_3697.jpg
    'op', # whether or not the post is the thread op (1 == yes, 0 == no)
    'op_num', # thread_num
    'capcode', # `capcode` - The capcode identifier for a post
    'trip', # `trip` - the user's tripcode, in format: !tripcode or !!securetripcode
    'spoiler', # `spoiler` - If the image was spoilered or not
    'poster_country', # country - Poster's ISO 3166-1 alpha-2 country code, https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
    'poster_hash', # an archiver construct
    'locked', # `closed` - if the thread is closed to replies
    'deleted', # `filedeleted` - if post had attachment and attachment is deleted
    'exif', # an archiver construct
    'comment', # `com` - Comment (HTML escaped)
    # 'tim', # `tim` - Unix timestamp + microtime that an image was uploaded. AQ does not use this.
)

@cache
def get_selector(board: str) -> str:
    """Remember to update `selector_columns` variable above when you modify these selectors.
    """
    SELECTOR = f"""
    SELECT
    {board}.thread_num,
    num,
    '{board}' AS board_shortname,
    timestamp_expired AS ts_expired,
    name,
    {board}.sticky AS sticky,
    coalesce(title, '') AS title,
    media_w AS media_w,
    media_h AS media_h,
    preview_w AS preview_w,
    preview_h AS preview_h,
    timestamp AS ts_unix,
    preview_orig,
    media_orig,
    {board}.media_hash,
    media_size AS media_size,
    media_filename AS media_filename,
    op as op,
    CASE WHEN op=1 THEN num ELSE {board}.thread_num END AS op_num,
    capcode AS capcode,
    trip,
    spoiler as spoiler,
    poster_country,
    poster_hash,
    {board}.locked AS locked,
    deleted AS deleted,
    exif,
    comment
    """

    return dedent(SELECTOR)


def validate_and_generate_params(form_data):
    """
    Removes inauthentic/non-form data (malicious POST fields, CSRF tags, etc.)
    Specifies the filters for each valid field.
    """
    param_filters = {
        'title': {'like': True, 's': 'title LIKE %(title)s'},
        'comment': {'like': True, 's': 'comment LIKE %(comment)s'},
        'media_filename': {'like': True, 's': 'media_filename LIKE %(media_filename)s'},
        'media_hash': {'s': 'media_hash = %(media_hash)s'},
        'num': {'s': 'num = %(num)s'},
        'date_before': {'s': 'timestamp <= %(date_before)s'},
        'date_after': {'s': 'timestamp >= %(date_after)s'},
        'has_no_file': {'s': 'media_filename is null or media_filename = ""'},
        'has_file': {'s': 'media_filename is not null and media_filename != ""'},
        'is_op': {'s': 'op = 1'},
        'is_not_op': {'s': 'op != 1'},
        'is_deleted': {'s': 'deleted = 1'},
        'is_not_deleted': {'s': 'deleted != 1'},
        'is_sticky': {'s': 'sticky = 1'},
        'is_not_sticky': {'s': 'sticky != 1'},
        'width': {'s': 'media_w = %(width)s'},
        'height': {'s': 'media_h = %(height)s'},
        'capcode': {'s': 'capcode = %(capcode)s'},
    }

    defaults_to_ignore = {
        'width': 0,
        'height': 0,
        'capcode': Capcode.default.value,
    }

    param_values = {}

    for field in param_filters:

        if 'like' in param_filters[field] and param_filters[field]['like'] and form_data[field]:
            param_values[field] = f'%{form_data[field]}%'

        elif form_data[field]:
            if (field in defaults_to_ignore) and (form_data[field] != defaults_to_ignore[field]):
                param_values[field] = form_data[field]
            elif field not in defaults_to_ignore:
                field_val = form_data[field]
                if isinstance(field_val, date) and 1970 <= field_val.year <= 2038:
                    field_val = int(datetime.combine(field_val, datetime.min.time()).timestamp())
                param_values[field] = field_val

    return param_values, param_filters


async def get_posts_filtered(form_data: dict, result_limit: int, order_by: str):
    """form_data e.g.
    ```
        form_data = dict(
            boards=['ck', 'mu'],
            title=None,
            comment='skill issue',
            media_filename=None,
            media_hash=None,
            has_file=False,
            is_op=False,
            ...
        )
    ```
    !IMPORTANT!
        form_data['boards'] is assumed to be validated before arriving here,
            like all other referenced to boards in this file.
    """

    if order_by not in ['asc', 'desc']:
        raise BadRequest('order_by is unknown')
    param_values, param_filters = validate_and_generate_params(form_data)

    sqls = []

    # With the Asagi schema, each board has its own table, so we loop over boards and do UNION ALLs to get multi-board sql results
    for board_shortname in form_data['boards']:

        s = f"""
            {get_selector(board_shortname)}
            FROM {board_shortname}
        """
        s += ' \n WHERE 1=1 '

        for field in param_values:
            s += f" \n and {param_filters[field]['s']} "

        sqls.append(s)

    sql = ' \n UNION ALL \n '.join(sqls)

    if sql.strip() == '':
        return {'posts': []}, {}  # no boards specified

    sql += f' \n ORDER BY ts_unix {order_by}'
    sql += f" \n LIMIT {int(result_limit) * len(form_data['boards'])} \n ;"

    posts = await query_dict(sql, params=param_values)

    result = {'posts': []}
    if not posts:
        return result, {}

    board_quotelinks = await get_post_replies(posts)
    
    # TODO: this post_2_quotelinks is wrong
    # it merges quotelinks from multiple boards together
    # the error must be fixed downstream
    # searching from from multiple boards should be allowed
    post_2_quotelinks = defaultdict(set)
    for _board, ql_lookup in board_quotelinks.items():
        for num, quotelinks in ql_lookup.items():
            post_2_quotelinks[num].update(quotelinks)
    
    for num in tuple(post_2_quotelinks.keys()):
        post_2_quotelinks[num] = list(post_2_quotelinks[num])

    _, posts = get_qls_and_posts(posts, gather_qls=False)
    result['posts'] = posts
    return result, post_2_quotelinks


def get_qls_and_posts(rows: list[dict], gather_qls: bool=True) -> tuple[dict, list]:
    post_2_quotelinks = defaultdict(list)
    posts = []
    for row in rows:
        row_quotelinks, row['comment'] = restore_comment(
            row['thread_num'],
            row['comment'],
            row['board_shortname']
        )

        if gather_qls:
            for row_quotelink in row_quotelinks:
                post_2_quotelinks[row_quotelink].append(row['num'])

        if row['title']:
            row['title'] = html.escape(row['title'])

        posts.append(row)

    return post_2_quotelinks, posts

async def get_post_replies(posts: list[dict]) -> dict[str, dict[int, list[int]]]:
    board_threads = defaultdict(set)
    
    for post in posts:
        board_threads[post['board_shortname']].add(post['op_num'])
    boards_threads = [(board, tuple(threads)) for board, threads in board_threads.items()]

    board_qls = await asyncio.gather(*(
        get_board_thread_quotelinks(board, threads)
        for board, threads in boards_threads
    ))
    board_quotelinks = {
        b_threads[0]: ql_lookup
        for b_threads, ql_lookup in zip(board_threads, board_qls)
    }
    return board_quotelinks

async def get_board_thread_quotelinks(board: str, thread_nums: tuple[int]):
    rows = await query_dict(f'''
        select num, comment
        from {board}
        where
            comment is not null
            and thread_num in ({Phg().size(thread_nums)})''',
        params=thread_nums
    )
    return get_quotelink_lookup(rows)


async def get_op_thread_count(board: str) -> int:
    rows = await query_tuple(f'select count(*) from {board}_threads;')
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


def restore_comment(op_num: int, comment: str, board_shortname: str):
    """
    Re-convert asagi stripped comment into clean html.
    Also create a dictionary with keys containing the post_num, which maps to a tuple containing the posts it links to.

    Returns a string (the processed comment) and a list of quotelinks in
    the post.

    greentext: a line that begins with a single ">" and ends with a '\n'
    redirect: a line that begins with a single ">>", has a thread number afterward that exists in the current thread or another thread (may be inline)

    >> (show OP)
    >>>/g/ (board redirect)
    >>>/g/<post_num> (board post redirect)
    """

    quotelinks = []

    GT = '&gt;'
    GTGT = "&gt;&gt;"

    if comment is None:
        return [], ''

    lines = html_highlight(html.escape(comment)).split("\n")
    for i, line in enumerate(lines):
        # >green text
        if GT == line[:4] and GT != line[4:8]:
            lines[i] = f"""<span class="quote">{line}</span>"""
            continue

        # >>123456789
        elif line.startswith(GTGT):
            tokens = line.split(" ")

            for j, token in enumerate(tokens):
                if token[:8] == GTGT and token[8:].isdigit():
                    quotelinks.append(int(token[8:]))
                    tokens[j] = f"""<a href="/{board_shortname}/thread/{op_num}#p{token[8:]}" class="quotelink" data-board_shortname="{board_shortname}">{token}</a>"""

            lines[i] = " ".join(tokens)

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
    page_num -= 1  # start from 0 offset when running queries

    threads_q = f'''
        select
            thread_num,
            nreplies,
            nimages,
            time_bump
        from {board}_threads
        ORDER BY time_bump DESC
        LIMIT 10
        OFFSET {Phg()()}
    '''
    if not (threads := await query_dict(threads_q, params=(page_num,))):
        return {'threads': []}

    thread_phs = Phg().size(threads)
    
    op_query = f'''
    {get_selector(board)}
    from {board}
    where
        op = 1
        and thread_num in ({thread_phs})
    '''
    
    replies_query = f'''
    with latest_replies AS (
        select
            num as reply_num,
            ROW_NUMBER() OVER (
                PARTITION BY {board}.thread_num order by {board}.num desc
            ) AS reply_number
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

    ops, replies = await asyncio.gather(
        query_dict(op_query, params=thread_nums),
        query_dict(replies_query, params=thread_nums),
    )

    reply_qls = get_quotelink_lookup(replies)
    for reply in replies:
        reply['quotelinks'] = reply_qls.get(reply['num'], [])
        _, reply['comment'] = restore_comment(reply['op_num'], reply['comment'], board)
    
    thread_posts = defaultdict(list)
    for op in ops:
        op_num = op['num']
        _, op['comment'] = restore_comment(op_num, op['comment'], board)
        op.update(thread_nums_d[op_num])
        thread_posts[op_num].append(op)
    for reply in replies:
        thread_posts[reply['op_num']].append(reply)

    return {
        'threads': [
            {'posts': thread_posts[thread['thread_num']]}
            for thread in threads
        ]
    }

async def generate_catalog(board: str, page_num: int=1):
    """Generates the catalog structure"""
    page_num -= 1  # start page number at 1

    phg = Phg()
    threads_q = f'''
        select
            thread_num,
            nreplies,
            nimages
        from {board}_threads
        ORDER BY time_bump DESC
        LIMIT 150
        OFFSET {phg()}
    '''
    if not (rows := await query_tuple(threads_q, (page_num,))):
        return []

    threads = {row[0]: row[1:] for row in rows}

    posts_q = f'''
        {get_selector(board)},
        {board}.media_hash,
        {board}_images.media AS media_orig,
        {board}_images.preview_op AS preview_orig
    FROM {board}
        LEFT JOIN {board}_images USING (media_id)
    where op = 1
    and thread_num in ({Phg().size(threads)})
    '''
    rows = await query_dict(posts_q, params=tuple(threads.keys()))
    
    batch_size = 15
    return [
        {
            "page": i,
            'threads': [{
                    **row,
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
    # Combine OP and replies into a single query to minimize database calls
    combined_query = f"""
        {get_selector(board)},
            threads.nreplies,
            threads.nimages,
            threads.time_bump,
            images.media_hash,
            images.media,
            images.preview_reply,
            images.preview_op
        FROM {board}
            LEFT JOIN {board}_threads AS threads USING (thread_num)
            LEFT JOIN {board}_images AS images USING (media_id)
        WHERE thread_num = {Phg()()}
        ORDER BY num ASC
    ;"""
    rows = await query_dict(combined_query, params=(thread_num,))

    post_2_quotelinks, posts = get_qls_and_posts(rows)

    results = {'posts': posts}

    return post_2_quotelinks, results


async def generate_post(board: str, post_id: int) -> tuple[dict]:
    """Returns {thread_num: 123, comment: 'hello', ...}"""
    sql = f"""
        {get_selector(board)}
        FROM {board}
        WHERE num = {Phg()()}
    ;"""
    posts = await query_dict(sql, params=(post_id,))

    if not posts:
        return None, None

    post_2_quotelinks, posts = get_qls_and_posts(posts)
    return post_2_quotelinks, posts[0]
