from quart import Blueprint, Response, abort, current_app, jsonify

from asagi_converter import (
    generate_catalog,
    generate_index,
    generate_post,
    generate_thread,
    get_counts_from_posts,
    get_op_thread_count
)
from boards import get_title
from configs import app_conf
from moderation import fc
from moderation.auth import (
    load_web_usr_data,
    web_usr_is_admin,
    web_usr_logged_in
)
from paginate import Pagination
from posts.template_optimizer import (
    get_posts_t,
    get_posts_t_thread,
    render_catalog_card,
    render_wrapped_post_t,
    wrap_post_t
)
from render import render_controller
from templates import (
    template_board_index,
    template_catalog,
    template_index,
    template_thread
)
from threads import render_thread_stats
from utils import Perf
from utils.validation import validate_board, validate_threads
from moderation.report import generate_report_form
from security import inject_csrf_token_to_session


bp = Blueprint("bp_web_app", __name__)


async def make_pagination_board_index(board: str, index: dict, page_num: int) -> Pagination:
    op_thread_count = await get_op_thread_count(board)
    op_thread_removed_count = await fc.get_op_thread_removed_count(board)
    op_thread_count -= op_thread_removed_count

    board_index_thread_count = len(index['threads'])

    # https://flask-paginate.readthedocs.io/en/master/
    return Pagination(
        page=page_num,
        display_msg=f'Displaying <b>{board_index_thread_count}</b> threads. <b>{op_thread_count}</b> threads in total.',
        total=op_thread_count,
        search=False,
        record_name='threads',
        href=f'/{board}/page/' + '{0}',
        show_single_page=True,
    )


@bp.get("/")
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def v_index(is_admin: bool, logged_in: bool):
    return await render_controller(
        template_index,
        logo_filename='logo.png',
        logged_in=logged_in,
        is_admin=is_admin,
    )


@bp.route('/robots.txt')
async def robots():
    if app_conf['allow_robots']:
        abort(404)
    content = 'User-agent: *\nDisallow: /'
    return Response(content, mimetype='text/plain')


@bp.route('/favicon.ico')
async def favicon():
    return await current_app.send_static_file('favicon.gif')


@bp.get("/<string:board>")
@inject_csrf_token_to_session
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def v_board_index(board: str, is_admin: bool, logged_in: bool):
    validate_board(board)
    p = Perf('index', enabled=app_conf.get('testing'))

    index, quotelinks = await generate_index(board)
    p.check('query')

    index['threads'] = [{'posts': await fc.filter_reported_posts(posts['posts'], is_authority=logged_in)} for posts in index['threads']]
    p.check('filter_reported')

    validate_threads(index['threads'])
    p.check('validate')

    pagination = await make_pagination_board_index(board, index, 0)
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
        pagination=pagination,
        threads=threads,
        board=board,
        title=get_title(board),
        logged_in=logged_in,
        is_admin=is_admin,
        report_form_t=generate_report_form(),
    )
    p.check('render')
    print(p)

    return rendered


@bp.get("/<string:board>/page/<int:page_num>")
@inject_csrf_token_to_session
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def v_board_index_page(board: str, page_num: int, is_admin: bool, logged_in: bool):
    p = Perf('index page', enabled=app_conf.get('testing'))
    validate_board(board)
    p.check('validate board')

    index, quotelinks = await generate_index(board, page_num)
    p.check('generate index')

    index['threads'] = [{'posts': await fc.filter_reported_posts(posts['posts'], is_authority=logged_in)} for posts in index['threads']]
    p.check('filter_reported')

    validate_threads(index['threads'])
    p.check('validate thread')

    pagination = await make_pagination_board_index(board, index, page_num)
    p.check('paginate')

    threads = '<hr>'.join(
        render_thread_stats(thread['posts'][0]) +
        get_posts_t(thread['posts'], quotelinks)
        for thread in index["threads"]
    )
    p.check('post_t')

    title = get_title(board)
    rendered = template_board_index.render(
        pagination=pagination,
        threads=threads,
        board=board,
        title=title,
        tab_title=title,
        logged_in=logged_in,
        is_admin=is_admin,
        report_form_t=generate_report_form(),
    )
    p.check('rendered')
    print(p)

    return rendered


async def make_pagination_catalog(board: str, catalog: list[dict], page_num: int) -> Pagination:
    op_thread_count = await get_op_thread_count(board)
    op_thread_removed_count = await fc.get_op_thread_removed_count(board)
    op_thread_count -= op_thread_removed_count

    catalog_pages = int(op_thread_count / 15) + 1  # we grab 150 threads per catalog page

    catalog_page_thread_count = 0
    for c in catalog:
        catalog_page_thread_count += len(c['threads'])

    # https://flask-paginate.readthedocs.io/en/master/
    return Pagination(
        page=page_num,
        display_msg=f'Displaying <b>{catalog_page_thread_count}</b> threads. <b>{op_thread_count}</b> threads in total.',
        total=catalog_pages,
        search=False,
        record_name='threads',
        href=f'/{board}/catalog/' + '{0}',
        show_single_page=True,
    )


@bp.get("/<string:board>/catalog")
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def v_catalog(board: str, is_admin: bool, logged_in: bool):
    validate_board(board)

    p = Perf('catalog', enabled=app_conf.get('testing'))
    catalog = await generate_catalog(board)
    p.check('query')

    # `nreplies` won't always be correct, but it does not effect paging
    catalog = [page | {'threads': (await fc.filter_reported_posts(page['threads'], is_authority=logged_in))} for page in catalog]
    p.check('filter_reported')

    pagination = await make_pagination_catalog(board, catalog, 0)
    p.check('paginate')

    threads = ''.join(
        render_catalog_card(wrap_post_t(op), show_nuke_btn=is_admin)
        for batch in catalog
        for op in batch['threads']
    )
    render = template_catalog.render(
        threads=threads,
        pagination=pagination,
        board=board,
        title=get_title(board),
        tab_title=f"/{board}/ Catalog",
        logged_in=logged_in,
        is_admin=is_admin,
    )
    p.check('render')
    print(p)

    return render


@bp.get("/<string:board>/catalog/<int:page_num>")
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def v_catalog_page(board: str, page_num: int, is_admin: bool, logged_in: bool):
    validate_board(board)

    p = Perf('catalog page', enabled=app_conf.get('testing'))
    catalog = await generate_catalog(board, page_num)
    p.check('query')

    # `nreplies` won't always be correct, but it does not effect paging
    catalog = [page | {'threads': (await fc.filter_reported_posts(page['threads'], is_authority=logged_in))} for page in catalog]
    p.check('filter_reported')

    pagination = await make_pagination_catalog(board, catalog, page_num)
    p.check('paginate')

    threads = ''.join(
        render_catalog_card(wrap_post_t(op), show_nuke_btn=is_admin)
        for batch in catalog
        for op in batch['threads']
    )
    render = template_catalog.render(
        threads=threads,
        pagination=pagination,
        board=board,
        title=get_title(board),
        tab_title=f"/{board}/ Catalog",
        logged_in=logged_in,
        is_admin=is_admin,
    )
    p.check('render')
    print(p)

    return render


@bp.get("/<string:board>/thread/<int:thread_num>")
@inject_csrf_token_to_session
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def v_thread(board: str, thread_num: int, is_admin: bool, logged_in: bool):
    validate_board(board)

    p = Perf('thread', enabled=app_conf.get('testing'))
    # use the existing json app function to grab the data
    post_2_quotelinks, thread_dict = await generate_thread(board, thread_num)
    p.check('queries')

    thread_dict['posts'] = await fc.filter_reported_posts(thread_dict['posts'], is_authority=logged_in)
    p.check('filter_reported')

    # TODO: only count manually if we can't get the counts from the side tables
    nreplies, nimages = get_counts_from_posts(thread_dict['posts'])

    validate_threads(thread_dict['posts'])
    p.check('validate')

    # posts_t = get_posts_t(thread_dict['posts'], post_2_quotelinks)
    posts_t = get_posts_t_thread(thread_dict['posts'], post_2_quotelinks)
    p.check('posts_t')

    title = f"/{board}/ #{thread_num}"

    render = template_thread.render(
        posts_t=posts_t,
        nreplies=nreplies,
        nimages=nimages,
        board=board,
        thread_num=thread_num,
        tab_title=title,
        logged_in=logged_in,
        is_admin=is_admin,
        report_form_t=generate_report_form(),
    )
    p.check('rendered')
    print(p)
    return render


@bp.get("/<string:board>/post/<int:post_id>")
async def v_post(board: str, post_id: int):
    """Called by the client to generate posts not on the page - e.g. when viewing search results.
    """
    validate_board(board)

    p = Perf('post', enabled=app_conf.get('testing'))
    post_2_quotelinks, post = await generate_post(board, post_id)
    p.check('query')

    if not post:
        return {}

    is_removed = await fc.is_post_removed(post.board_shortname, post.num)
    p.check('is_post_removed')
    if is_removed:
        return {}

    html_content = render_wrapped_post_t(wrap_post_t(post | dict(quotelinks={})))

    p.check('render')
    print(p)
    return jsonify(html_content=html_content)
