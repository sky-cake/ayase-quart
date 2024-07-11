import quart_flask_patch  # isort: skip

from datetime import datetime
from logging import getLogger
from time import perf_counter

from orjson import loads
from quart import Blueprint
from werkzeug.exceptions import BadRequest

from asagi_converter import get_posts_filtered, restore_comment
from configs import CONSTS
from forms import IndexSearchConfigForm, SearchForm
from search import index_board
from search_providers import SearchQuery, get_search_provider
from templates import (
    template_error_404,
    template_index,
    template_index_search,
    template_index_search_config,
    template_search
)
from utils import (
    highlight_search_results,
    render_controller,
    validate_board_shortname
)

search_p = get_search_provider()
search_log = getLogger('search')

blueprint_search = Blueprint("blueprint_search", __name__)


@blueprint_search.route("/index_search_config", methods=['GET', 'POST'])
async def index_search_config():
    form = await IndexSearchConfigForm.create_form()
    if await form.validate_on_submit():
        match form.operation.data:
            case 'init':
                await search_p.init_indexes()
                await search_p.config_posts()
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
    )

@blueprint_search.errorhandler(404)
async def error_not_found(e):
    return await render_controller(
        template_error_404,
        message='404 Not Found',
        **CONSTS.render_constants,
        tab_title=f'Error'
    )


@blueprint_search.errorhandler(400)
async def error_invalid(e):
    return await render_controller(
        template_error_404,
        e=e.description,
        message='The search parameters will result in 0 records.',
        **CONSTS.render_constants,
        tab_title=f'Invalid search'
    )


@blueprint_search.get("/")
async def v_index():
    return await render_controller(
        template_index,
        **CONSTS.render_constants,
        tab_title=CONSTS.site_name
    )

@blueprint_search.route("/index_search", methods=['GET', 'POST'])
async def v_index_search():
    if not CONSTS.search:
        raise BadRequest('search is disabled')
    
    form = await SearchForm.create_form()
    search_mode = 'index'
    searched = False

    posts = []
    quotelinks = []
    start = perf_counter()
    if await form.validate_on_submit():
        
        if not form.boards.data: raise BadRequest('select a board')
        for board in form.boards.data:
            validate_board_shortname(board)

        if form.search_mode.data == 'gallery' and form.has_no_file.data: raise BadRequest("search mode 'gallery' only shows files")
        if form.search_mode.data not in ['index', 'gallery']: raise BadRequest('search_mode is unknown')
        if form.order_by.data not in ['asc', 'desc']: raise BadRequest('order_by is unknown')
        if form.is_op.data and form.is_not_op.data: raise BadRequest('is_op is contradicted')
        if form.is_deleted.data and form.is_not_deleted.data: raise BadRequest('is_deleted is contradicted')
        if form.has_file.data and form.has_no_file.data: raise BadRequest('has_file is contradicted')
        if form.date_before.data and form.date_after.data and (form.date_before.data < form.date_after.data): raise BadRequest('the dates are contradicted')

        params = form.data
        terms = params['title'] or params['comment']

        q = SearchQuery(
            terms=terms,
            boards=params['boards']
        )
        if params['num']:
            q.num = int(params['num'])
        if params['result_limit']:
            q.result_limit = int(params['result_limit'])
        if params['media_filename']:
            q.media_file = params['media_filename']
        if params['media_hash']:
            q.media_hash = params['media_hash']
        if params['has_file']:
            q.file = True
        if params['has_no_file']:
            q.file = False
        if params['is_op']:
            q.op = True
        if params['is_not_op']:
            q.op = False
        if params['is_deleted']:
            q.deleted = True
        if params['is_not_deleted']:
            q.deleted = False
        if params['date_after']:
            dt = datetime.combine(params['date_after'], datetime.min.time())
            q.after = int(dt.timestamp())
        if params['date_before']:
            dt = datetime.combine(params['date_before'], datetime.min.time())
            q.before = int(dt.timestamp())

        parsed_query = perf_counter() - start
        search_log.warning(f'{parsed_query=:.4f}')

        results = await search_p.search_posts(q)

        got_search = perf_counter() - start
        search_log.warning(f'{got_search=:.4f}')

        posts = []
        for result in results:
            post = loads(result['data'])
            formatted = result['_formatted']
            op_num = post['no'] if post['resto'] == 0 else post['resto']
            if formatted['comment']:
                _, post['com'] = restore_comment(op_num, formatted['comment'], post['board_shortname'])
            posts.append(post)

        posts.sort(key=lambda x: x['time'], reverse=form.order_by.data == 'desc')
            
        searched = True
        
        if form.search_mode.data == 'gallery':
            search_mode = 'gallery'

    patched_posts = perf_counter() - start
    search_log.warning(f'{patched_posts=:.4f}')

    rend = await render_controller(
        template_index_search,
        search_mode=search_mode,
        form=form,
        posts=posts,
        searched=searched,
        quotelinks=quotelinks,
        search_result=True,
        tab_title=CONSTS.site_name,
        **CONSTS.render_constants
    )

    rendered = perf_counter() - start
    search_log.warning(f'{rendered=:.4f}')

    return rend

@blueprint_search.route("/search", methods=['GET', 'POST'])
async def v_search():
    if not CONSTS.search:
        raise BadRequest('search is disabled')
    
    form = await SearchForm.create_form()
    search_mode = 'index'
    searched = False

    posts = []
    quotelinks = []
    if await form.validate_on_submit():
        
        if not form.boards.data: raise BadRequest('select a board')
        for board in form.boards.data:
            validate_board_shortname(board)

        if form.search_mode.data == 'gallery' and form.has_no_file.data: raise BadRequest("search mode 'gallery' only shows files")
        if form.search_mode.data not in ['index', 'gallery']: raise BadRequest('search_mode is unknown')
        if form.order_by.data not in ['asc', 'desc']: raise BadRequest('order_by is unknown')
        if form.is_op.data and form.is_not_op.data: raise BadRequest('is_op is contradicted')
        if form.is_deleted.data and form.is_not_deleted.data: raise BadRequest('is_deleted is contradicted')
        if form.has_file.data and form.has_no_file.data: raise BadRequest('has_file is contradicted')
        if form.date_before.data and form.date_after.data and (form.date_before.data < form.date_after.data): raise BadRequest('the dates are contradicted')

        params = form.data
        
        posts, quotelinks = await get_posts_filtered(params, form.result_limit.data, form.order_by.data) # posts = {'posts': [{...}, {...}, ...]}

        if CONSTS.search_result_highlight:
            posts = highlight_search_results(form, posts)
            
        posts = posts['posts']
        searched = True
        
        if form.search_mode.data == 'gallery':
            search_mode = 'gallery'

    return await render_controller(
        template_search,
        search_mode=search_mode,
        form=form,
        posts=posts,
        searched=searched,
        quotelinks=quotelinks,
        search_result=True,
        tab_title=CONSTS.site_name,
        **CONSTS.render_constants
    )
