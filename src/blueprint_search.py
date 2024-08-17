import quart_flask_patch  # isort: skip

from logging import getLogger
from time import perf_counter

from quart import Blueprint, request
from werkzeug.exceptions import BadRequest

from asagi_converter import get_posts_filtered, restore_comment
from configs import CONSTS, SearchMode
from forms import IndexSearchConfigForm, SearchForm
from posts.template_optimizer import get_gallery_media_t, wrap_post_t
from search.highlighting import get_term_re, mark_highlight
from search.loader import index_board
from search.pagination import total_pages, template_pagination_links
from search.providers import get_search_provider
from search.query import get_search_query
from templates import (
    template_error_404,
    template_index,
    template_index_search,
    template_index_search_config,
    template_index_search_gallery_post_t,
    template_index_search_post_t,
    template_search
)
from utils import (
    highlight_search_results,
    render_controller,
    validate_board_shortname
)

search_log = getLogger('search')

blueprint_search = Blueprint("blueprint_search", __name__)


@blueprint_search.route("/index_search_config", methods=['GET', 'POST'])
async def index_search_config():
    search_p = get_search_provider()
    form = await IndexSearchConfigForm.create_form()
    if await form.validate_on_submit():
        match form.operation.data:
            case 'init':
                await search_p.init_indexes()
                msg = 'Index initialized.'
            case 'populate':
                boards = form.boards.data
                if not boards:
                    msg = 'No board(s) selected.'
                else:
                    for board in boards:
                        await index_board(board, search_p)
                    msg = f'Index populated with data from [{", ".join(boards)}]'
            case 'wipe':
                await search_p.posts_wipe()
                msg = 'Index data wiped.'
            case _:
                msg = 'Unknown operation.'
    else:
        msg = 'Choose an action to run.'

    return await render_controller(
        template_index_search_config,
        **CONSTS.render_constants,
        tab_title=CONSTS.site_name,
        form=form,
        msg=msg,
        board_list=' '.join(CONSTS.boards_in_database),
    )


@blueprint_search.route("/index_stats", methods=['GET'])
async def index_search_stats():
    search_p = get_search_provider()
    return await search_p.post_stats()


@blueprint_search.errorhandler(404)
async def error_not_found(e):
    return await render_controller(template_error_404, message='404 Not Found', **CONSTS.render_constants, tab_title=f'Error')


@blueprint_search.errorhandler(400)
async def error_invalid(e):
    return await render_controller(
        template_error_404, e=e.description, message='The search parameters will result in 0 records.', **CONSTS.render_constants, tab_title=f'Invalid search'
    )


@blueprint_search.get("/")
async def v_index():
    return await render_controller(template_index, **CONSTS.render_constants, tab_title=CONSTS.site_name)


@blueprint_search.route("/index_search", methods=['GET', 'POST'])
async def v_index_search():
    if not CONSTS.search:
        raise BadRequest('search is disabled')

    search_mode = SearchMode.index
    searched = False
    cur_page = None
    pages = None
    total_hits = None

    posts_t = []
    results = []
    quotelinks = []
    page_links = ''
    start = perf_counter()
    search_p = get_search_provider()

    if request.method == 'POST':
        form = await SearchForm.create_form()
    else:
        boards = request.args.getlist('boards')
        params = {**request.args}
        params['boards'] = boards
        form = await SearchForm.create_form(**params)
    
    valid = await form.validate()
    
    if valid and form.boards.data:
        searched = True

        if not form.boards.data:
            raise BadRequest('select a board')
        for board in form.boards.data:
            validate_board_shortname(board)

        if form.search_mode.data == SearchMode.gallery and form.has_no_file.data:
            raise BadRequest("search mode SearchMode.gallery only shows files")
        if form.search_mode.data not in [SearchMode.index, SearchMode.gallery]:
            raise BadRequest('search_mode is unknown')
        if form.order_by.data not in ['asc', 'desc']:
            raise BadRequest('order_by is unknown')
        if form.is_op.data and form.is_not_op.data:
            raise BadRequest('is_op is contradicted')
        if form.is_deleted.data and form.is_not_deleted.data:
            raise BadRequest('is_deleted is contradicted')
        if form.has_file.data and form.has_no_file.data:
            raise BadRequest('has_file is contradicted')
        if form.date_before.data and form.date_after.data and (form.date_before.data < form.date_after.data):
            raise BadRequest('the dates are contradicted')

        if form.search_mode.data == SearchMode.gallery:
            search_mode = SearchMode.gallery

        q = get_search_query(form.data)

        parsed_query = perf_counter() - start
        search_log.warning(f'  {parsed_query=:.4f} +{parsed_query:.4f}')

        results, total_hits = await search_p.search_posts(q)
        pages = total_pages(total_hits, q.result_limit)
        cur_page = q.page
        page_links = template_pagination_links('/index_search', form.data, pages, cur_page)

        done_search = perf_counter() - start
        search_log.warning(f'   {done_search=:.4f} +{done_search-parsed_query:.4f}')

        if search_mode == SearchMode.index:
            hl_re = get_term_re(q.terms) if q.terms else None
            for post in results:
                op_num = post['no'] if post['resto'] == 0 else post['resto']
                if post['comment']:
                    if hl_re:
                        post['comment'] = mark_highlight(hl_re, post['comment'])
                    _, post['comment'] = restore_comment(op_num, post['comment'], post['board_shortname'])

                posts_t.append(wrap_post_t(post))

        patched_posts = perf_counter() - start
        search_log.warning(f' {patched_posts=:.4f} +{patched_posts-done_search:.4f}')

        if search_mode == SearchMode.index:
            posts_t = ''.join(template_index_search_post_t.render(**p) for p in posts_t)
        else:
            posts_t = ''.join(template_index_search_gallery_post_t.render(post=post, t_gallery_media=get_gallery_media_t(post)) for post in results)

        rendered_posts = perf_counter() - start
        search_log.warning(f'{rendered_posts=:.4f} +{rendered_posts-patched_posts:.4f}')

    rend = template_index_search.render(
        search_mode=search_mode,
        form=form,
        posts_t=posts_t,
        page_links=page_links,
        res_count=len(results),
        searched=searched,
        quotelinks=quotelinks,
        search_result=True,
        tab_title=CONSTS.site_name,
        cur_page=cur_page,
        pages=pages,
        total_hits=total_hits,
    )

    if searched:
        rendered_page = perf_counter() - start
        search_log.warning(f' {rendered_page=:.4f} +{rendered_page-rendered_posts:.4f}')

    return rend


@blueprint_search.route("/search", methods=['GET', 'POST'])
async def v_search():
    if not CONSTS.search:
        raise BadRequest('search is disabled')

    form = await SearchForm.create_form()
    search_mode = SearchMode.index
    searched = False

    posts = []
    quotelinks = []
    if await form.validate_on_submit():

        if not form.boards.data:
            raise BadRequest('select a board')
        for board in form.boards.data:
            validate_board_shortname(board)

        if form.search_mode.data == SearchMode.gallery and form.has_no_file.data:
            raise BadRequest("search mode SearchMode.gallery only shows files")
        if form.search_mode.data not in [SearchMode.index, SearchMode.gallery]:
            raise BadRequest('search_mode is unknown')
        if form.order_by.data not in ['asc', 'desc']:
            raise BadRequest('order_by is unknown')
        if form.is_op.data and form.is_not_op.data:
            raise BadRequest('is_op is contradicted')
        if form.is_deleted.data and form.is_not_deleted.data:
            raise BadRequest('is_deleted is contradicted')
        if form.has_file.data and form.has_no_file.data:
            raise BadRequest('has_file is contradicted')
        if form.date_before.data and form.date_after.data and (form.date_before.data < form.date_after.data):
            raise BadRequest('the dates are contradicted')

        params = form.data

        posts, quotelinks = await get_posts_filtered(params, form.result_limit.data, form.order_by.data)  # posts = {'posts': [{...}, {...}, ...]}

        if CONSTS.search_result_highlight:
            posts = highlight_search_results(form, posts)

        posts = posts['posts']
        searched = True

        if form.search_mode.data == SearchMode.gallery:
            search_mode = SearchMode.gallery

    return await render_controller(
        template_search,
        search_mode=search_mode,
        form=form,
        posts=posts,
        searched=searched,
        quotelinks=quotelinks,
        search_result=True,
        tab_title=CONSTS.site_name,
        **CONSTS.render_constants,
    )
