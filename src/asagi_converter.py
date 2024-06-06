import html
from configs import CONSTS
from db import query_execute
from typing import List, Dict, Any
import asyncio
import re
from textwrap import dedent
from werkzeug.exceptions import BadRequest


def get_selector(board_shortname, double_percent=True):
    if CONSTS.db_aiomysql:
        SELECTOR = """
        SELECT
        `{board_shortname}`.`thread_num`,
        `num` AS `no`,
        '{board_shortname}' AS `board_shortname`,
        DATE_FORMAT(FROM_UNIXTIME(`timestamp`), "%m/%d/%y (%a) %H:%i:%S") AS `now`,
        DATE_FORMAT(FROM_UNIXTIME(`timestamp_expired`), "%m/%d/%y (%a) %H:%i:%S") AS `deleted_time`,
        `name`,
        `{board_shortname}`.`sticky`,
        (CASE WHEN `title` IS NULL THEN '' ELSE `title` END) AS `sub`,
        `media_w` AS `w`,
        `media_h` AS `h`,
        `preview_w` AS `tn_w`,
        `preview_h` AS `tn_h`,
        `timestamp` AS `time`,
        `preview_orig` AS `asagi_preview_filename`,
        `media_orig` AS `asagi_filename`,
        (CASE WHEN `media_orig` IS NULL THEN timestamp * 1000 ELSE SUBSTRING_INDEX(media_orig, '.', 1) END) AS `tim`,
        `{board_shortname}`.`media_hash` AS `md5`,
        `media_size` AS `fsize`,
        (CASE WHEN `media_filename` IS NULL THEN NULL ELSE SUBSTRING_INDEX(media_filename, '.', 1) END) AS `filename`,
        (CASE WHEN `media_filename` IS NULL THEN NULL ELSE SUBSTRING_INDEX(media_filename, '.', -1) END) AS `ext`,
        (CASE WHEN op=1 THEN CAST(0 AS UNSIGNED) ELSE `{board_shortname}`.`thread_num` END) AS `resto`,
        (CASE WHEN capcode='N' THEN NULL ELSE `capcode` END) AS `capcode`,
        `trip`,
        `spoiler`,
        `poster_country` AS `country`,
        `poster_hash`,
        `{board_shortname}`.`locked` AS `closed`,
        `deleted` AS `filedeleted`,
        `exif`,
        `comment` AS `com`
        """
        if double_percent:
            SELECTOR = SELECTOR.replace('%', '%%')
    elif CONSTS.db_aiosqlite:
        SELECTOR = """
        SELECT
        {board_shortname}.thread_num,
        num AS no,
        '{board_shortname}' AS board_shortname,
        datetime(timestamp, 'unixepoch') AS now,
        datetime(timestamp_expired, 'unixepoch') AS deleted_time,
        name,
        {board_shortname}.sticky,
        CASE WHEN title IS NULL THEN '' ELSE title END AS sub,
        media_w AS w,
        media_h AS h,
        preview_w AS tn_w,
        preview_h AS tn_h,
        timestamp AS time,
        preview_orig AS asagi_preview_filename,
        media_orig AS asagi_filename,
        CASE WHEN media_orig IS NULL THEN timestamp * 1000 ELSE substr(media_orig, 1, instr(media_orig, '.') - 1) END AS tim,
        {board_shortname}.media_hash AS md5,
        media_size AS fsize,
        CASE WHEN media_filename IS NULL THEN NULL ELSE substr(media_filename, 1, instr(media_filename, '.') - 1) END AS filename,
        CASE WHEN media_filename IS NULL THEN NULL ELSE substr(media_filename, instr(media_filename, '.') + 1) END AS ext,
        CASE WHEN op=1 THEN CAST(0 AS INTEGER) ELSE {board_shortname}.thread_num END AS resto,
        CASE WHEN capcode='N' THEN NULL ELSE capcode END AS capcode,
        trip,
        spoiler,
        poster_country AS country,
        poster_hash,
        {board_shortname}.locked AS closed,
        deleted AS filedeleted,
        exif,
        comment AS com
        """
    else:
        raise ValueError(CONSTS.db_aiomysql, CONSTS.db_aiosqlite)

    SELECTOR = dedent(SELECTOR).format(board_shortname=board_shortname)
    return SELECTOR


def get_image_selector():
    MD5_IMAGE_SELECTOR = "`media_hash`,`media`,`preview_reply`,`preview_op`"
    return MD5_IMAGE_SELECTOR


def validate_and_generate_params(form_data):
    """
    Removes inauthentic/non-form data (malicious POST fields, CSRF tags, etc.)
    Specifies the filters for each valid field.
    """

    param_filters = {
        'title': {
            'like': True,
            's': '`title` LIKE %(title)s'
        },
        'comment': {
            'like': True,
            's': '`comment` LIKE %(comment)s'
        },
        'media_filename': {
            'like': True,
            's': '`media_filename` LIKE %(media_filename)s'
        },
        'media_hash': {
            's': '`media_hash` = %(media_hash)s'
        },
        'num': {
            's': '`num` = %(num)s'
        },
        'date_before': {
            's': '`timestamp` <= UNIX_TIMESTAMP(%(date_before)s)'
        },
        'date_after': {
            's': '`timestamp` >= UNIX_TIMESTAMP(%(date_after)s)'
        },
        'has_no_file': {
            's': '`media_filename` is null'
        },
        'has_file': {
            's': '`media_filename` is not null'
        },
        'is_op': {
            's': '`op` = 1'
        },
        'is_not_op': {
            's': '`op` != 1'
        },
        'is_deleted': {
            's': '`deleted` = 1'
        },
        'is_not_deleted': {
            's': '`deleted` != 1'
        },
    }

    param_values = {}

    for field in param_filters:

        if 'like' in param_filters[field] and param_filters[field]['like'] and form_data[field]:
            param_values[field] = f'%{form_data[field]}%'

        elif form_data[field]:
            param_values[field] = form_data[field]

    return param_values, param_filters


async def get_posts_filtered(form_data: Dict[Any, Any], result_limit: int, order_by: str):
    """Params e.g.
    ```
        params = dict(
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

    if order_by not in ['asc', 'desc']: raise BadRequest('order_by is unknown')
    param_values, param_filters = validate_and_generate_params(form_data)

    sqls = []

    # With the Asagi schema, each board has its own table, so we loop over boards and do UNION ALLs to get multi-board sql results
    for board_shortname in form_data['boards']:

        s =  get_selector(board_shortname)
        s += f' \n FROM `{board_shortname}`'
        s +=  ' \n WHERE 1=1 '
        
        for field in param_values:
            s += f" \n and {param_filters[field]['s']} "

        sqls.append(s)

    sql = ' \n UNION ALL \n '.join(sqls)

    if sql.strip() == '':
        return {'posts': []}, {} # no boards specified
    
    sql +=  f' \n ORDER BY time {order_by}'
    sql += f" \n LIMIT {int(result_limit) * len(form_data['boards'])} \n ;"
    
    posts = await query_execute(sql, params=param_values)

    images = []
    for p in posts:
        i = await get_post_images(board_shortname, p['no'])
        images.append(i)
    return await convert_standalone_posts(posts, images)


async def convert_standalone_posts(posts, medias, return_quotelinks=True):
    """Converts asagi API data to 4chan API format for posts that don't include
    an entire thread of data (e.g. search results, or other random posts grouped together).
    """

    result = {'posts': []}
    quotelink_map = {}
    for post, media in zip(posts, medias):
        if media:
            if post['md5'] != media['media_hash']:
                raise ValueError('Not equal: ', post['md5'], media['media_hash'])
                
            if(post["resto"] == 0):
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
                    if quotelink not in quotelink_map:
                        quotelink_map[quotelink] = []
                    quotelink_map[quotelink].append(reply["no"])

        _, post['com'] = restore_comment(op_num, post['com'], post['board_shortname'])
        result['posts'].append(post)
    return result, quotelink_map


async def get_post_replies(board_shortname, thread_num, post_num):
    comment = f'%>>{int(post_num)}%'
    SELECT_POST_REPLIES = get_selector(board_shortname) + f"FROM `{board_shortname}` WHERE `comment` LIKE %(comment)s AND `thread_num` = %(thread_num)s;"
    return await query_execute(SELECT_POST_REPLIES, params={'thread_num': thread_num, 'comment': comment})


async def get_post(board_shortname:str, post_num: int):
    SELECT_POST = get_selector(board_shortname) + f"FROM `{board_shortname}` WHERE `num`=%(post_num)s"
    return await query_execute(SELECT_POST, params={'post_num': post_num}, fetchone=True)


async def get_post_images(board_shortname:str, post_num: int):
    image_selector=get_image_selector()
    SELECT_POST_IMAGES = f"SELECT {image_selector} FROM `{board_shortname}_images` WHERE `media_hash` IN (SELECT `media_hash` FROM `{board_shortname}` WHERE `num`=%(post_num)s)"

    return await query_execute(SELECT_POST_IMAGES, params={'post_num': post_num}, fetchone=True)


async def get_thread(board_shortname:str, thread_num: int):
    SELECT_THREAD = get_selector(board_shortname) + f"FROM `{board_shortname}` WHERE `thread_num`=%(thread_num)s ORDER BY `num`"
    return await query_execute(SELECT_THREAD, params={'thread_num': thread_num})


async def get_thread_images(board_shortname:str, thread_num: int):
    image_selector=get_image_selector()
    SELECT_THREAD_IMAGES = f"SELECT {image_selector} FROM `{board_shortname}_images` WHERE `media_hash` IN (SELECT `media_hash` FROM `{board_shortname}` WHERE `thread_num`=%(thread_num)s)"

    return await query_execute(SELECT_THREAD_IMAGES, params={'thread_num': thread_num})


async def get_thread_details(board_shortname:str, thread_num: int):
    SELECT_THREAD_DETAILS = f"SELECT `nreplies`, `nimages` FROM `{board_shortname}_threads` WHERE `thread_num`=%(thread_num)s"
    return await query_execute(SELECT_THREAD_DETAILS, params={'thread_num': thread_num}, fetchone=True)


async def get_thread_preview(board_shortname:str, thread_num: int):
    SELECT_THREAD_PREVIEW = get_selector(board_shortname) + f"FROM `{board_shortname}` WHERE `thread_num`=%(thread_num)s ORDER BY `num` DESC LIMIT 5" 
    return await query_execute(SELECT_THREAD_PREVIEW, params={'thread_num': thread_num})


async def get_thread_preview_images(board_shortname:str, thread_num: int):
    image_selector=get_image_selector()
    SELECT_THREAD_PREVIEW_IMAGES = f"SELECT {image_selector} FROM `{board_shortname}_images` WHERE `media_hash` IN (SELECT `media_hash` FROM `{board_shortname}` WHERE `thread_num`=%(thread_num)s ORDER BY `num`)"  

    return await query_execute(SELECT_THREAD_PREVIEW_IMAGES, params={'thread_num': thread_num})


async def get_op_list(board_shortname:str, page_num: int):
    SELECT_OP_LIST_BY_OFFSET = get_selector(board_shortname) + f"FROM {board_shortname} INNER JOIN {board_shortname}_threads ON `{board_shortname}_threads`.`thread_num` = `{board_shortname}`.`thread_num` WHERE OP=1 ORDER BY `time_bump` DESC LIMIT 10 OFFSET %(page_num)s;"
    return await query_execute(SELECT_OP_LIST_BY_OFFSET, params={'page_num': page_num * 10})


async def get_op_images(board_shortname:str, md5s: list):
    if not md5s:
        raise NotImplementedError(md5s)

    image_selector=get_image_selector()
    placeholders = ','.join(['%s'] * len(md5s))
    SELECT_OP_IMAGE_LIST_BY_MEDIA_HASH = f"SELECT {image_selector} FROM `{board_shortname}_images` WHERE `media_hash` IN ({placeholders})"

    return await query_execute(SELECT_OP_IMAGE_LIST_BY_MEDIA_HASH, params=md5s)


async def get_op_details(board_shortname:str, thread_nums: List[int]):
    if not thread_nums:
        raise NotImplementedError(thread_nums)
    
    thread_nums = [int(x) for x in thread_nums]
    placeholders = ','.join(['%s'] * len(thread_nums))
    SELECT_OP_DETAILS_LIST_BY_THREAD_NUM = f"SELECT `thread_num`, `nreplies`, `nimages` FROM `{board_shortname}_threads` WHERE `thread_num` IN ({placeholders})"
    results = await query_execute(SELECT_OP_DETAILS_LIST_BY_THREAD_NUM, params=thread_nums)
    return sorted(results, key=lambda x: x['thread_num'])


async def get_catalog_threads(board_shortname:str, page_num: int):
    SELECT_GALLERY_THREADS_BY_OFFSET = get_selector(board_shortname) + f"FROM `{board_shortname}` INNER JOIN `{board_shortname}_threads` ON `{board_shortname}`.`thread_num` = `{board_shortname}_threads`.`thread_num` WHERE OP=1 ORDER BY `{board_shortname}_threads`.`time_bump` DESC LIMIT 150 OFFSET %(page_num)s;"
    return await query_execute(SELECT_GALLERY_THREADS_BY_OFFSET, params={'page_num': page_num * 150})


async def get_catalog_images(board_shortname:str, page_num: int):
    SELECT_GALLERY_THREAD_IMAGES_MD5 = f"SELECT `{board_shortname}`.media_hash, `{board_shortname}_images`.`media`, `{board_shortname}_images`.`preview_reply`, `{board_shortname}_images`.`preview_op` FROM ((`{board_shortname}` INNER JOIN `{board_shortname}_threads` ON `{board_shortname}`.`thread_num` = `{board_shortname}_threads`.`thread_num`) INNER JOIN `{board_shortname}_images` ON `{board_shortname}_images`.`media_hash` = `{board_shortname}`.`media_hash`) WHERE OP=1 ORDER BY `{board_shortname}_threads`.`time_bump` DESC LIMIT 150 OFFSET %(page_num)s;"
    return await query_execute(SELECT_GALLERY_THREAD_IMAGES_MD5, params={'page_num': page_num})


async def get_catalog_details(board_shortname:str, page_num: int):
    SELECT_GALLERY_THREAD_DETAILS = f"SELECT `nreplies`, `nimages` FROM `{board_shortname}_threads` ORDER BY `time_bump` DESC LIMIT 150 OFFSET %(page_num)s"
    return await query_execute(SELECT_GALLERY_THREAD_DETAILS, params={'page_num': page_num})


def get_text_quotelinks(text: str):
    """Given some escaped post/comment, `text`, returns a list of all the quotelinks (>>123456) in it.
    """
    quotelinks = []
    lines = html.escape(text).split("\n") # text = '>>20074095\n>>20074101\nYou may be buying the wrong eggs'

    GTGT = "&gt;&gt;"
    for i, line in enumerate(lines):

        if line.startswith(GTGT):
            tokens = line.split(" ")
            for token in tokens:
                if token[:8] == GTGT and token[8:].isdigit():
                    quotelinks.append(token[8:])

    return quotelinks # quotelinks = ['20074095', '20074101']


def substitute_square_brackets(text):
    if re.fullmatch(r'.*\[(spoiler|code|banned)\].*\[/(spoiler|code|banned)\].*', text):
        pattern_spoiler = re.compile(r'\[spoiler\](.*?)\[/spoiler\]', re.DOTALL) # with re.DOTALL, the dot matches any character, including newline characters.
        pattern_code = re.compile(r'\[code\](.*?)\[/code\]', re.DOTALL) # ? makes the (.*) non-greedy
        pattern_banned = re.compile(r'\[banned\](.*?)\[/banned\]', re.DOTALL)

        text = re.sub(pattern_spoiler, r'<span class="spoiler">\1</span>', text)
        text = re.sub(pattern_code, r'<code><pre>\1</pre></code>', text)
        text = re.sub(pattern_banned, r'<span class="banned">\1</span>', text)
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

    lines = html.escape(com).split("\n")
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


async def generate_index(board_shortname: str, page_num: int, html=True):
    """Generates the board index"""

    page_num -= 1  # start from 0 when running queries
    op_list = await convert_thread_ops(board_shortname, page_num)
    # for each thread, get the first 5 posts and put them in 'threads'
    threads = []
    for op in op_list:
        thread_id = op["posts"][0]["no"]
        asagi_thread, quotelinks = await convert_thread_preview(board_shortname, thread_id)

        # determine number of omitted posts
        omitted_posts = (
            op["posts"][0]["replies"] - len(asagi_thread["posts"]) - 1
        )  # subtract OP
        op["posts"][0]["omitted_posts"] = omitted_posts

        # determine number of omitted images
        num_images_shown = 0
        for i in range(len(asagi_thread["posts"])):
            post = asagi_thread["posts"][i]
            if post["md5"] and post["resto"] != 0:
                num_images_shown += 1
            # add quotelinks to thread
            if html:
                asagi_thread["posts"][i]["quotelinks"] = quotelinks

        omitted_images = op["posts"][0]["images"] - num_images_shown
        if op["posts"][0]["md5"]:
            omitted_images -= 1  # subtract OP if OP has image

        op["posts"][0]["omitted_images"] = omitted_images

        combined = {}
        # if the thread has only one post, don't repeat OP post.
        if op["posts"][0]["replies"] == 0:
            combined = op
        else:
            combined["posts"] = op["posts"] + asagi_thread["posts"]

        threads.append(combined)

    # encapsulate threads around a dict
    result = {}
    result["threads"] = threads

    return result


async def get_op_thread_count(board_shortname) -> int:
    return (await query_execute(f"select count(*) as op_thread_count from {board_shortname} where OP=1;", fetchone=True))['op_thread_count']


async def generate_catalog(board_shortname: str, page_num: int):
    """Generates the catalog structure"""

    page_num -= 1  # start page number at 1

    thread_list, details, images = await asyncio.gather(
        get_catalog_threads(board_shortname, page_num),
        get_catalog_details(board_shortname, page_num),
        get_catalog_images(board_shortname, page_num)
    )

    catalog_list = convert(thread_list, details, images, is_catalog=True)

    result = []
    page_threads = {"page": 0, "threads": []}
    for i in range(len(thread_list)):
        # new page every 15 threads
        if i % 15 == 0 and i != 0:
            result.append(page_threads)
            page_threads = {"page": (i // 14) + 1, "threads": []}
        page_threads["threads"].append(catalog_list[i])
    # add the last page threads
    result.append(page_threads)
    return result



async def convert_post(board_shortname: str, post_id: int):
    """Generates a single post"""

    post, images = await asyncio.gather(
        get_post(board_shortname, post_id),
        get_post_images(board_shortname, post_id)
    )
    
    post = [post]
    images = [images]
    return convert(post, images=images, is_post=True)


async def convert_thread_ops(board_shortname: str, page_num: int):
    """Generate the OP post"""

    op_list = await get_op_list(board_shortname, page_num)
    if not op_list:
        return convert([], [], [], is_ops=True)

    op_image_list, op_detail_list = await asyncio.gather(
        get_op_images(board_shortname, [op.md5 for op in op_list]),
        get_op_details(board_shortname, [op.no for op in op_list])
    )

    thread_ops = convert(op_list, op_detail_list, op_image_list, is_ops=True)
    return thread_ops


async def convert_thread_preview(board_shortname: str, thread_id: int):
    """Generate a thread preview, removing OP post"""

    thread, images = await asyncio.gather(
        get_thread_preview(board_shortname, thread_id),
        get_thread_preview_images(board_shortname, thread_id)
    )

    for i in range(len(thread)):
        if thread[i]["resto"] == 0:
            del thread[i]

    thread.reverse()
    return convert(thread, images=images)


async def convert_thread(board_shortname: str, thread_id: int):
    """Convert threads to 4chan api"""

    thread, images, details = await asyncio.gather(
        get_thread(board_shortname, thread_id),
        get_thread_images(board_shortname, thread_id),
        get_thread_details(board_shortname, thread_id)
    )
    details = [details] # details needs to be an array
    return convert(thread, details, images)


def convert(thread, details=None, images=None, is_ops=False, is_post=False, is_catalog=False):
    """Converts asagi API data to 4chan API format."""

    result = {}
    quotelink_map = {}
    posts = []
    for i in range(len(thread)):
        if not thread or not thread[i]:
            continue

        posts.append(dict(thread[i])) # The record object doesn't support assignment so we convert it to a normal dict

        if images:
            for image in images:
                if image and image["media_hash"] == posts[i]["md5"]:
                    if(posts[i]["resto"] == 0):
                        posts[i]["asagi_preview_filename"] = image["preview_op"]
                    else:
                        posts[i]["asagi_preview_filename"] = image["preview_reply"]
                    posts[i]["asagi_filename"] = image["media"]

        if details and posts[i]["resto"] == 0:
            posts[i]["replies"] = details[i].get("nreplies", None)
            posts[i]["images"] = details[i].get("nimages", None)

        if not is_catalog:
            if posts[i]['resto'] == 0:
                op_num = posts[i]['no']
            else:
                op_num = posts[i]['resto']
        
            post_quotelinks, posts[i]["com"] = restore_comment(op_num, posts[i]["com"], posts[i]['board_shortname'])
            for quotelink in post_quotelinks:
                if quotelink not in quotelink_map:
                    quotelink_map[quotelink] = []
                quotelink_map[quotelink].append(posts[i]["no"])

    if is_post:
        return posts, quotelink_map

    if is_catalog:
        return posts

    if is_ops:
        result = []
        for op in posts:
            result.append({"posts": [op]})
        return result

    result["posts"] = posts
    return result, quotelink_map
