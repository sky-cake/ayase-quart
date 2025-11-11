import hashlib
import html
import time
from datetime import timedelta

from quart import Blueprint, current_app, flash, redirect, request, url_for
from quart_rate_limiter import rate_limit

from asagi_converter import (
    generate_catalog,
    generate_thread,
    get_counts_from_posts
)
from configs import archiveposting_conf
from db import db_a
from forms import PostForm
from moderation import fc
from moderation.auth import (
    load_web_usr_data,
    web_usr_is_admin,
    web_usr_logged_in
)
from posts.capcodes import Capcode
from posts.template_optimizer import (
    get_posts_t_archiveposting,
    render_catalog_card_archiveposting,
    wrap_post_t
)
from security.captcha import MathCaptcha
from templates import template_catalog, template_thread
from utils.validation import validate_threads

bp = Blueprint("bp_web_archiveposting", __name__)


def get_sha256_from_str(s: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(s.encode('utf-8'))
    return hasher.hexdigest()


def get_ip():
    ip = request.headers.get('Remote-Addr')
    if ip:
        return ip

    ip = request.headers.get('X-Forwarded-For')

    if ',' in ip:
        return ip.split(',')[-1].strip()

    return ip


async def get_new_thread_num(table: str) -> int:
    row = await db_a.query_tuple(f'SELECT COALESCE(MAX(thread_num), 0) + 1 FROM `{table}`')
    return int(row[0][0])


async def get_new_num(table: str) -> int:
    row = await db_a.query_tuple(f'SELECT COALESCE(MAX(num), 0) + 1 FROM `{table}`')
    return int(row[0][0])


def get_threads_d(post):
    return dict(
        thread_num=post['thread_num'],
        time_op=post['timestamp'],
        time_last=0,
        time_bump=0,
        time_last_modified=0,
        nreplies=0,
        nimages=0,
        sticky=0,
        locked=0,
    )


async def create_thread(table: str, post: dict) -> int:
    num = await get_new_num(table)
    post['num'] = num
    post['thread_num'] = num

    sql_cols = ', '.join(post)
    sql = f"""insert into `{table}` ({sql_cols}) values ({db_a.Phg().size(post)});"""

    params = list(post.values())
    await db_a.query_tuple(sql, params=params, commit=True)

    threads_d = get_threads_d(post)

    sql_cols = ', '.join(threads_d)
    sql = f"""insert into `{table}_threads` ({sql_cols}) values ({db_a.Phg().size(threads_d)});"""

    await db_a.query_tuple(sql, params=list(threads_d.values()), commit=True)
    return num


async def create_post(table: str, post: dict):
    if 'thread_num' not in post:
        raise ValueError()

    num = await get_new_num(table)
    post['num'] = num

    sql_cols = ', '.join(post)

    sql = f"""insert into `{table}` ({sql_cols}) values ({db_a.Phg().size(post)});"""

    params = list(post.values())
    await db_a.query_tuple(sql, params=params, commit=True)


def get_post_d(p: dict) -> dict:
    return {
        'poster_ip': get_ip(),
        'timestamp': int(time.time()),
        'thread_num': p.get('thread_num'),
        'op': 1 if p.get('op') else 0,

        # escape these when rendering html
        'title': p.get('title', None),
        'comment': p.get('comment', None),

        'capcode': p.get('capcode') if p.get('capcode') else Capcode.user,
        'name': None,
        'trip': None,
        'media_id': 0,
        'subnum': 0,
        'timestamp_expired': 0,
        'preview_orig': None,
        'preview_w': 0,
        'preview_h': 0,
        'media_filename': None,
        'media_w': 0,
        'media_h': 0,
        'media_size': 0,
        'media_hash': None,
        'media_orig': None,
        'spoiler': 0,
        'deleted': 0,
        'email': None,
        'delpass': None,
        'sticky': 0,
        'locked': 0,
        'poster_hash': None,
        'poster_country': None,
        'exif': None,
    }


@bp.post(f'/{archiveposting_conf['board_name']}/catalog')
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
@rate_limit(1, timedelta(minutes=20))
async def post_archiveposting_catalog(is_admin: bool, logged_in: bool):
    return await _archiveposting_catalog(is_admin, logged_in)


@bp.get(f'/{archiveposting_conf['board_name']}/catalog')
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def get_archiveposting_catalog(is_admin: bool, logged_in: bool):
    return await _archiveposting_catalog(is_admin, logged_in)


async def _archiveposting_catalog(is_admin: bool, logged_in: bool):
    board = archiveposting_conf['board_name']
    form: PostForm = await PostForm.create_form()
    captcha = MathCaptcha(tff_file_path=current_app.config["MATH_CAPTCHA_FONT"])

    if request.method == 'POST' and (await form.validate_on_submit()):
        if captcha.is_valid(form.captcha_id.data, form.captcha_answer.data):
            form_data = form.data
            form_data['op'] = True

            if is_admin:
                form_data['capcode'] = Capcode.admin

            p = get_post_d(form_data)

            # thread_num = await create_thread(board, p)
            await create_thread(board, p)
            await flash("Post created!", "success")

            # return redirect(url_for('bp_web_archiveposting.get_archiveposting_thread', thread_num=thread_num))
            return redirect(url_for('bp_web_archiveposting.get_archiveposting_catalog'))
        else:
            await flash("Wrong math captcha answer.", "danger")

    catalog = await generate_catalog(board, db_X=db_a)

    # `nreplies` won't always be correct, but it does not effect paging
    catalog = [page | {'threads': (await fc.filter_reported_posts(page['threads'], is_authority=logged_in))} for page in catalog]

    threads = ''.join(
        render_catalog_card_archiveposting(wrap_post_t(op))
        for batch in catalog
        for op in batch['threads']
    )
    form.captcha_id.data, form.captcha_b64_img_str = captcha.generate_captcha()
    render = template_catalog.render(
        archiveposting_form=form,
        form_message='New Thread',
        threads=threads,
        board=board,
        tab_title=f"/{board}/ Catalog",
        logged_in=logged_in,
        is_admin=is_admin,
    )
    return render


@bp.get(f'/{archiveposting_conf['board_name']}/thread/<int:thread_num>')
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def get_archiveposting_thread(is_admin: bool, logged_in: bool, thread_num: int):
    return await _archiveposting_thread(is_admin, logged_in, thread_num)


@bp.post(f'/{archiveposting_conf['board_name']}/thread/<int:thread_num>')
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
@rate_limit(1, timedelta(minutes=5))
async def post_archiveposting_thread(is_admin: bool, logged_in: bool, thread_num: int):
    return await _archiveposting_thread(is_admin, logged_in, thread_num)


async def _archiveposting_thread(is_admin: bool, logged_in: bool, thread_num: int):
    board = archiveposting_conf['board_name']
    form: PostForm = await PostForm.create_form()
    captcha = MathCaptcha(tff_file_path=current_app.config["MATH_CAPTCHA_FONT"])

    if request.method == 'POST' and (await form.validate_on_submit()):
        if captcha.is_valid(form.captcha_id.data, form.captcha_answer.data):
            form_data = form.data
            form_data['op'] = False
            form_data['thread_num'] = thread_num

            if is_admin:
                form_data['capcode'] = Capcode.admin

            p = get_post_d(form_data)
            await create_post(board, p)

            form.data.clear()
            await flash("Post created!", "success")
            return redirect(url_for('bp_web_archiveposting.get_archiveposting_thread', thread_num=thread_num))
        else:
            await flash("Wrong math captcha answer.", "danger")

    # use the existing json app function to grab the data
    post_2_quotelinks, thread_dict = await generate_thread(board, thread_num, db_X=db_a)

    thread_dict['posts'] = await fc.filter_reported_posts(thread_dict['posts'], is_authority=logged_in)

    nreplies, nimages = get_counts_from_posts(thread_dict['posts'])

    validate_threads(thread_dict['posts'])

    posts_t = get_posts_t_archiveposting(thread_dict['posts'], post_2_quotelinks)

    title = f"/{board}/ #{thread_num}"
    form.captcha_id.data, form.captcha_b64_img_str = captcha.generate_captcha()
    render = template_thread.render(
        archiveposting_form=form,
        form_message='Reply',
        posts_t=posts_t,
        nreplies=nreplies,
        nimages=nimages,
        board=board,
        title=title,
        tab_title=title,
        logged_in=logged_in,
        is_admin=is_admin,
    )
    return render
