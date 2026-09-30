from quart import Blueprint

from ...asagi_converter import generate_index, get_op_thread_count
from ...boards import get_title
from ...moderation import fc
from ...moderation.auth_web import (
     load_web_usr_data,
     web_usr_is_admin,
     web_usr_logged_in
 )
from ...moderation.report import generate_report_form
from ...posts.template_optimizer import get_posts_t
from ...search.pagination import get_total_pages, template_pagination_links
from ...security import inject_csrf_token_to_session
from ...templates import template_board_index
from ...threads import render_thread_stats
from ...perf import Perf
from ...utils.validation import validate_board_query_parameter


bp = Blueprint("bp_web_thread", __name__)


async def make_pagination_board_index(board: str, index: dict, page_num: int):
    op_thread_count = await get_op_thread_count(board)
    # op_thread_removed_count = await fc.get_op_thread_removed_count(board)
    # op_thread_count -= op_thread_removed_count

    board_index_thread_count = len(index['threads'])

    info = f'Displaying <b>{board_index_thread_count:,}</b> threads. <b>{op_thread_count:,}</b> threads in total.'

    index_post_count = 10  # threads per index page
    page_links = template_pagination_links(
        path=f'/{board}/page',
        params={'page': page_num},
        total_pages=get_total_pages(op_thread_count, index_post_count),
    )

    return info, page_links


@bp.get("/<string:board>")
@inject_csrf_token_to_session
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
@validate_board_query_parameter
async def v_board_index(board: str, is_admin: bool, logged_in: bool):
    p = Perf('index')

    index, quotelinks = await generate_index(board)
    p.check('query')

    index['threads'] = [{'posts': await fc.filter_reported_posts(posts['posts'], is_authority=logged_in)} for posts in index['threads']]
    p.check('filter_reported')

    p.check('validate')

    pagination_info, pagination_links = await make_pagination_board_index(board, index, 0)
    p.check('pagination')

    threads = '<hr>'.join(
        render_thread_stats(thread['posts'][0]) +
        get_posts_t(thread['posts'], quotelinks)
        for thread in index["threads"]
        if thread['posts']
    )
    p.check('post_t')

    rendered = template_board_index.render(
        tab_title=f'/{board}/ Index',
        pagination_info=pagination_info,
        pagination_links=pagination_links,
        threads=threads,
        board=board,
        title=get_title(board),
        logged_in=logged_in,
        is_admin=is_admin,
        report_form_t=generate_report_form(),
    )
    p.check('render')
    p.emit()

    return rendered


@bp.get("/<string:board>/page/<int:page_num>")
@inject_csrf_token_to_session
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
@validate_board_query_parameter
async def v_board_index_page(board: str, page_num: int, is_admin: bool, logged_in: bool):
    p = Perf('index page')

    index, quotelinks = await generate_index(board, page_num)
    p.check('generate index')

    index['threads'] = [{'posts': await fc.filter_reported_posts(posts['posts'], is_authority=logged_in)} for posts in index['threads']]
    p.check('filter_reported')

    p.check('validate thread')

    pagination_info, pagination_links = await make_pagination_board_index(board, index, page_num)
    p.check('paginate')

    threads = '<hr>'.join(
        render_thread_stats(thread['posts'][0]) +
        get_posts_t(thread['posts'], quotelinks)
        for thread in index["threads"]
        if thread['posts']
    )
    p.check('post_t')

    title = get_title(board)
    rendered = template_board_index.render(
        pagination_info=pagination_info,
        pagination_links=pagination_links,
        threads=threads,
        board=board,
        title=title,
        tab_title=title,
        logged_in=logged_in,
        is_admin=is_admin,
        report_form_t=generate_report_form(),
    )
    p.check('rendered')
    p.emit()

    return rendered
