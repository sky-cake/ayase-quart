import html
import re
from collections import defaultdict
from functools import cache
from textwrap import dedent

from quart import current_app
from werkzeug.exceptions import BadRequest

from configs import CONSTS
from enums import DbType, SearchMode
from posts.capcodes import Capcode
from search.highlighting import html_highlight

selector_columns = (
    'thread_num', 'no', 'board_shortname', 'now', 'deleted_time', 'name',
    'sticky', 'sub', 'w', 'h', 'tn_w', 'tn_h', 'time',
    'asagi_preview_filename', 'asagi_filename', 'tim', 'md5',
    'fsize', 'filename', 'ext', 'resto', 'capcode', 'trip',
    'spoiler', 'country', 'poster_hash', 'closed', 'filedeleted', 'exif', 'com'
)

@cache
def get_selector(board_shortname, double_percent=True):
    """Remember to update `selector_columns` when you modify these selectors.
    """
    if CONSTS.db_type == DbType.mysql:
        SELECTOR = """
        SELECT
        `{board_shortname}`.`thread_num`,
        `num` AS `no`,
        '{board_shortname}' AS `board_shortname`,
        DATE_FORMAT(FROM_UNIXTIME(`timestamp`), "%m/%d/%y (%a) %H:%i:%S") AS `now`,
        CASE WHEN `timestamp_expired` IS NULL THEN 0 ELSE DATE_FORMAT(FROM_UNIXTIME(`timestamp_expired`), "%m/%d/%y (%a) %H:%i:%S") END AS `deleted_time`,
        `name`,
        CAST(COALESCE(`{board_shortname}`.`sticky`, 0) AS UNSIGNED) AS sticky,
        (CASE WHEN `title` IS NULL THEN '' ELSE `title` END) AS `sub`,
        CAST(COALESCE(`media_w`, 0) AS UNSIGNED) AS `w`,
        CAST(COALESCE(`media_h`, 0) AS UNSIGNED) AS `h`,
        CAST(COALESCE(`preview_w`, 0) AS UNSIGNED) AS `tn_w`,
        CAST(COALESCE(`preview_h`, 0) AS UNSIGNED) AS `tn_h`,
        `timestamp` AS `time`,
        `preview_orig` AS `asagi_preview_filename`,
        `media_orig` AS `asagi_filename`,
        (CASE WHEN `media_orig` IS NULL THEN timestamp * 1000 ELSE SUBSTRING_INDEX(media_orig, '.', 1) END) AS `tim`,
        `{board_shortname}`.`media_hash` AS `md5`,
        CAST(COALESCE(`media_size`, 0) AS UNSIGNED) AS `fsize`,
        (CASE WHEN `media_filename` IS NULL THEN NULL ELSE SUBSTRING_INDEX(media_filename, '.', 1) END) AS `filename`,
        (CASE WHEN `media_filename` IS NULL THEN NULL ELSE SUBSTRING_INDEX(media_filename, '.', -1) END) AS `ext`,
        (CASE WHEN op=1 THEN CAST(0 AS UNSIGNED) ELSE `{board_shortname}`.`thread_num` END) AS `resto`,
        (CASE WHEN capcode='N' THEN NULL ELSE `capcode` END) AS `capcode`,
        `trip`,
        CAST(COALESCE(`spoiler`, 0) AS UNSIGNED) as spoiler,
        `poster_country` AS `country`,
        `poster_hash`,
        CAST(COALESCE(`{board_shortname}`.`locked`, 0) AS UNSIGNED) AS `closed`,
        CAST(COALESCE(`deleted`, 0) AS UNSIGNED) AS `filedeleted`,
        `exif`,
        `comment` AS `com`
        """
        if double_percent:
            SELECTOR = SELECTOR.replace('%', '%%')
    elif CONSTS.db_type == DbType.sqlite:
        SELECTOR = """
        SELECT
        {board_shortname}.thread_num,
        num AS no,
        '{board_shortname}' AS board_shortname,
        datetime(timestamp, 'unixepoch') AS now,
        CASE WHEN timestamp_expired IS NULL THEN 0 ELSE datetime(timestamp_expired, 'unixepoch') END AS deleted_time,
        name,
        CAST(COALESCE({board_shortname}.sticky, 0) AS UNSIGNED) as sticky,
        CASE WHEN title IS NULL THEN '' ELSE title END AS sub,
        CAST(COALESCE(media_w, 0) AS UNSIGNED) AS w,
        CAST(COALESCE(media_h, 0) AS UNSIGNED) AS h,
        CAST(COALESCE(preview_w, 0) AS UNSIGNED) AS tn_w,
        CAST(COALESCE(preview_h, 0) AS UNSIGNED) AS tn_h,
        timestamp AS time,
        preview_orig AS asagi_preview_filename,
        media_orig AS asagi_filename,
        CASE WHEN media_orig IS NULL THEN timestamp * 1000 ELSE substr(media_orig, 1, instr(media_orig, '.') - 1) END AS tim,
        {board_shortname}.media_hash AS md5,
        CAST(COALESCE(media_size, 0) AS UNSIGNED) AS fsize,
        CASE WHEN media_filename IS NULL THEN NULL ELSE substr(media_filename, 1, instr(media_filename, '.') - 1) END AS filename,
        CASE WHEN media_filename IS NULL THEN NULL ELSE substr(media_filename, instr(media_filename, '.') + 1) END AS ext,
        CASE WHEN op=1 THEN CAST(0 AS UNSIGNED) ELSE {board_shortname}.thread_num END AS resto,
        CASE WHEN capcode='N' THEN NULL ELSE capcode END AS capcode,
        trip,
        CAST(COALESCE(spoiler, 0) AS UNSIGNED) as spoiler,
        poster_country AS country,
        poster_hash,
        CAST(COALESCE({board_shortname}.locked, 0) AS UNSIGNED) AS closed,
        CAST(COALESCE(deleted, 0) AS UNSIGNED) AS filedeleted,
        exif,
        comment AS com
        """
    else:
        raise ValueError(CONSTS.db_type)

    SELECTOR = dedent(SELECTOR).format(board_shortname=board_shortname)
    return SELECTOR


def get_image_selector():
    MD5_IMAGE_SELECTOR = "`media_hash`,`media`,`preview_reply`,`preview_op`"
    return MD5_IMAGE_SELECTOR


def construct_date_filter(param_name):
    if CONSTS.db_type == DbType.mysql:
        if param_name == 'date_before':
            return f"`timestamp` <= UNIX_TIMESTAMP(%({param_name})s)"
        elif param_name == 'date_after':
            return f"`timestamp` >= UNIX_TIMESTAMP(%({param_name})s)"
        else:
            raise ValueError(f"Unsupported operator: {param_name}")

    elif CONSTS.db_type == DbType.sqlite:
        if param_name == 'date_before':
            return f"`timestamp` <= strftime('%s', %({param_name})s)"
        elif param_name == 'date_after':
            return f"`timestamp` >= strftime('%s', %({param_name})s)"
        else:
            raise ValueError(f"Unsupported operator: {param_name}")

    else:
        raise ValueError("Unsupported database type")


def validate_and_generate_params(form_data):
    """
    Removes inauthentic/non-form data (malicious POST fields, CSRF tags, etc.)
    Specifies the filters for each valid field.
    """
    param_filters = {
        'title': {'like': True, 's': '`title` LIKE %(title)s'},
        'comment': {'like': True, 's': '`comment` LIKE %(comment)s'},
        'media_filename': {'like': True, 's': '`media_filename` LIKE %(media_filename)s'},
        'media_hash': {'s': '`media_hash` = %(media_hash)s'},
        'num': {'s': '`num` = %(num)s'},
        'date_before': {'s': construct_date_filter('date_before')},
        'date_after': {'s': construct_date_filter('date_after')},
        'has_no_file': {'s': '`media_filename` is null or `media_filename` = ""'},
        'has_file': {'s': '`media_filename` is not null and `media_filename` != ""'},
        'is_op': {'s': '`op` = 1'},
        'is_not_op': {'s': '`op` != 1'},
        'is_deleted': {'s': '`deleted` = 1'},
        'is_not_deleted': {'s': '`deleted` != 1'},
        'is_sticky': {'s': '`sticky` = 1'},
        'is_not_sticky': {'s': '`sticky` != 1'},
        'width': {'s': '`media_w` = %(width)s'},
        'height': {'s': '`media_h` = %(height)s'},
        'capcode': {'s': '`capcode` = %(capcode)s'},
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
                param_values[field] = form_data[field]

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

        s = get_selector(board_shortname)
        s += f' \n FROM `{board_shortname}`'
        s += ' \n WHERE 1=1 '

        for field in param_values:
            s += f" \n and {param_filters[field]['s']} "

        sqls.append(s)

    sql = ' \n UNION ALL \n '.join(sqls)

    if sql.strip() == '':
        return {'posts': []}, {}  # no boards specified

    sql += f' \n ORDER BY time {order_by}'
    sql += f" \n LIMIT {int(result_limit) * len(form_data['boards'])} \n ;"

    posts = await current_app.db.query_execute(sql, params=param_values)
    images = await get_post_images(board_shortname, [p['no'] for p in posts])

    num_to_image = {i['num']: i for i in images}

    images_sorted = []
    for p in posts:
        images_sorted.append(num_to_image.get(p['no'], None))

    return_quotelinks = form_data['search_mode'] == SearchMode.index
    return await convert_standalone_posts(posts, images_sorted, return_quotelinks=return_quotelinks)


async def convert_standalone_posts(posts, medias, return_quotelinks=True):
    """Converts asagi API data to 4chan API format for posts that don't include
    an entire thread of data (e.g. search results, or other random posts grouped together).
    """

    result = {'posts': []}
    post_2_quotelinks = {}
    for post, media in zip(posts, medias):
        if media:
            if post['md5'] != media['media_hash']:
                raise ValueError('Not equal: ', post['md5'], media['media_hash'])

            if post["resto"] == 0:
                post["asagi_preview_filename"] = media["preview_op"]
            else:
                post["asagi_preview_filename"] = media["preview_reply"]

            post["asagi_filename"] = media["media"]

        if post['resto'] == 0:
            op_num = post['no']
        else:
            op_num = post['resto']

        if return_quotelinks:
            replies = await get_post_replies(post['board_shortname'], op_num, post['no'])
            for reply in replies:
                post_quotelinks = get_text_quotelinks(reply["com"])

                for quotelink in post_quotelinks:
                    if quotelink not in post_2_quotelinks:
                        post_2_quotelinks[quotelink] = []
                    post_2_quotelinks[quotelink].append(reply["no"])

        _, post['com'] = restore_comment(op_num, post['com'], post['board_shortname'])
        if post['sub']:
            post['sub'] = html.escape(post['sub'])
        result['posts'].append(post)
    return result, post_2_quotelinks


async def get_post_replies(board_shortname, thread_num, post_num):
    comment = f'%>>{int(post_num)}%'
    SELECT_POST_REPLIES = get_selector(board_shortname) + f"FROM `{board_shortname}` WHERE `comment` LIKE %(comment)s AND `thread_num` = %(thread_num)s;"
    return await current_app.db.query_execute(SELECT_POST_REPLIES, params={'thread_num': thread_num, 'comment': comment})


async def get_post_images(board_shortname: str, post_nums: list[int]):
    image_selector = get_image_selector()

    placeholders = ','.join(['%s'] * len(post_nums))

    SELECT_POST_IMAGES = f"SELECT `num`, {image_selector} FROM `{board_shortname}_images` i INNER JOIN `{board_shortname}` USING (media_hash) WHERE `num` IN ({placeholders});"

    return await current_app.db.query_execute(SELECT_POST_IMAGES, params=post_nums)


async def get_op_thread_count(board_shortname) -> int:
    return (await current_app.db.query_execute(f"select count(*) as op_thread_count from {board_shortname} where OP=1;", fetchone=True))['op_thread_count']


def get_text_quotelinks(text: str):
    """Given some escaped post/comment, `text`, returns a list of all the quotelinks (>>123456) in it."""
    quotelinks = []
    lines = html.escape(text).split("\n")  # text = '>>20074095\n>>20074101\nYou may be buying the wrong eggs'

    GTGT = "&gt;&gt;"
    for i, line in enumerate(lines):

        if line.startswith(GTGT):
            tokens = line.split(" ")
            for token in tokens:
                if token[:8] == GTGT and token[8:].isdigit():
                    quotelinks.append(token[8:])

    return quotelinks  # quotelinks = ['20074095', '20074101']


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


def restore_comment(op_num: int, com: str, board_shortname: str):
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

    if com is None:
        return [], ''

    lines = html_highlight(html.escape(com)).split("\n")
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
                    quotelinks.append(token[8:])
                    tokens[j] = f"""<a href="/{board_shortname}/thread/{op_num}#p{token[8:]}" class="quotelink" data-board_shortname="{board_shortname}">{token}</a>"""

            lines[i] = " ".join(tokens)

    lines = "</br>".join(lines)
    lines = substitute_square_brackets(lines)

    return quotelinks, lines


def get_qls_and_posts(rows: list[dict]) -> tuple[dict, list]:
    post_2_quotelinks = defaultdict(list)
    posts = []
    for i, row in enumerate(rows):

        if row.get('md5'):
            if row.get('resto') == 0:
                row['asagi_preview_filename'] = row.pop('preview_op')
            else:
                row['asagi_preview_filename'] = row.pop('preview_reply')

            row['asagi_filename'] = row.pop('media')

        thread_num = row.get('thread_num')
        comment = row.get('com')
        board_shortname = row.get('board_shortname')

        row_quotelinks, row['com'] = restore_comment(thread_num, comment, board_shortname)

        for row_quotelink in row_quotelinks:
            post_2_quotelinks[row_quotelink].append(rows[i]["no"])

        posts.append(row)

    return post_2_quotelinks, posts


async def generate_index(board_shortname: str, page_num: int):
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

    # Combine OP and replies into a single query to minimize database calls
    combined_query = f"""
    WITH latest_ops AS (
        {get_selector(board_shortname)},
            threads.`nreplies`,
            threads.`nimages`,
            threads.`time_bump`,
            images.`media_hash`,
            images.`media`,
            images.`preview_reply`,
            images.`preview_op`,
            NULL as reply_number
        FROM `{board_shortname}`
            INNER JOIN `{board_shortname}_threads` AS threads USING (`thread_num`)
            LEFT JOIN `{board_shortname}_images` AS images USING (`media_id`)
        WHERE `OP` = 1
        ORDER BY `time_bump` DESC
        LIMIT 10
        OFFSET %(page_num)s -- OFFSET, present or absent, does not slow down the query
    ),
    latest_replies AS (
        {get_selector(board_shortname)},
            NULL AS `nreplies`,
            NULL AS `nimages`,
            NULL AS `time_bump`,
            images.`media_hash`,
            images.`media`,
            images.`preview_reply`,
            images.`preview_op`,
            ROW_NUMBER() OVER (PARTITION BY {board_shortname}.`thread_num` ORDER BY {board_shortname}.`num` DESC) AS reply_number
        FROM `{board_shortname}`
            LEFT JOIN `{board_shortname}_images` AS images USING (`media_id`)
        WHERE `thread_num` IN (SELECT thread_num FROM latest_ops) AND `OP` != 1
    )
    SELECT * FROM latest_ops
    UNION ALL
    SELECT * FROM latest_replies
    WHERE reply_number <= 3
    ;"""
    result = await current_app.db.query_execute(combined_query, params={'page_num': page_num})

    ops_result = [row for row in result if row['resto'] == 0]
    replies_result = [row for row in result if row['resto'] != 0]

    replies_by_thread = defaultdict(list)
    for reply in replies_result:
        replies_by_thread[reply['thread_num']].append(get_qls_and_posts([reply])[1][0])

    results = {'threads': []}
    for op in ops_result:
        thread_num = op['thread_num']
        thread_data = {'posts': [get_qls_and_posts([op])[1][0]]}
        if thread_num in replies_by_thread:
            thread_data['posts'].extend(replies_by_thread[thread_num])
        results['threads'].append(thread_data)

    return results


async def generate_catalog(board_shortname: str, page_num: int):
    """Generates the catalog structure"""
    page_num -= 1  # start page number at 1

    sql = f"""
        {get_selector(board_shortname)},
            nreplies,
            nimages,
            `{board_shortname}`.media_hash,
            `{board_shortname}_images`.`media` AS asagi_filename,
            `{board_shortname}_images`.`preview_op` AS asagi_preview_filename
        FROM `{board_shortname}`
            LEFT JOIN `{board_shortname}_threads` USING (thread_num)
            LEFT JOIN `{board_shortname}_images` USING (media_id)
        WHERE `OP`=1
        ORDER BY `time_bump` DESC
        LIMIT 150
        OFFSET %(page_num)s
    """
    rows = await current_app.db.query_execute(sql, params={'page_num': page_num})
    catalog_list = [dict(row) for row in rows]

    result = [
        {"page": i // 15, "threads": catalog_list[i:i + 15]}
        for i in range(0, len(catalog_list), 15)
    ]
    return result


async def generate_thread(board_shortname: str, thread_num: int) -> tuple[dict]:
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
        {get_selector(board_shortname)},
            threads.`nreplies`,
            threads.`nimages`,
            threads.`time_bump`,
            images.`media_hash`,
            images.`media`,
            images.`preview_reply`,
            images.`preview_op`
        FROM `{board_shortname}`
            LEFT JOIN `{board_shortname}_threads` AS threads USING (`thread_num`)
            LEFT JOIN `{board_shortname}_images` AS images USING (`media_id`)
        WHERE `thread_num` = %(thread_num)s
        ORDER BY `num` ASC
    ;"""
    rows = await current_app.db.query_execute(combined_query, params={'thread_num': thread_num})

    post_2_quotelinks, posts = get_qls_and_posts(rows)

    results = {'posts': posts}

    return post_2_quotelinks, results


async def generate_post(board_shortname: str, post_id: int) -> tuple[dict]:
    """Returns {thread_num: 123, com: 'hello', ...}"""
    sql = f"""
        {get_selector(board_shortname)},
            images.`media_hash`,
            images.`media`,
            images.`preview_reply`,
            images.`preview_op`
        FROM `{board_shortname}`
            LEFT JOIN `{board_shortname}_images` AS images USING (`media_id`)
        WHERE `num` = %(num)s
        LIMIT 1
    ;"""
    post = await current_app.db.query_execute(sql, params={'num': post_id}, fetchone=True)

    if not post:
        return None, None

    post_2_quotelinks, posts = get_qls_and_posts([post])
    post = posts[0]
    return post_2_quotelinks, post
