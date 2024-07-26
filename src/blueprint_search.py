import quart_flask_patch  # isort: skip

from datetime import datetime
from logging import getLogger
from time import perf_counter
import re

from quart import Blueprint
from werkzeug.exceptions import BadRequest

from asagi_converter import get_posts_filtered, restore_comment
from configs import CONSTS, IndexSearchType
from forms import IndexSearchConfigForm, SearchForm
from highlighting import get_term_re, mark_highlight
from posts.template_optimizer import wrap_post_t
from search import index_board
from search_providers import SearchQuery, get_search_provider
from templates import (
    template_error_404,
    template_index,
    template_index_post,
    template_index_search,
    template_index_search_config,
    template_search
)
from utils import (
    highlight_search_results,
    render_controller,
    validate_board_shortname
)

search_log = getLogger('search')

blueprint_search = Blueprint("blueprint_search", __name__)

def total_pages(total: int, per_page: int) -> int:
    # -(-total // q.result_limit) # https://stackoverflow.com/a/35125872
    if not total:
        return 0
    d, m = divmod(total, per_page)
    if m > 0:
        return d + 1
    return d


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
    )


@blueprint_search.route("/index_stats", methods=['GET'])
async def index_search_stats():
    search_p = get_search_provider()
    return await search_p.post_stats()


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
    cur_page = None
    pages = None
    total_hits = None

    posts_t = []
    res_count = 0
    quotelinks = []
    start = perf_counter()
    search_p = get_search_provider()
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

        # this needs time to sort out and test
        # should consider using search engine apis so we dont need to worry about security
        match CONSTS.index_search_provider:
            case IndexSearchType.manticore:
                # https://manual.manticoresearch.com/Searching/Full_text_matching/Escaping#Escaping-characters-in-query-string
                chars_to_escape = ['\\', '!', '"', '$', "'", '(', ')', '-', '/', '<', '@', '^', '|', '~']

            case IndexSearchType.meili:
                # https://www.meilisearch.com/docs/reference/api/search#query-q
                # Errors when given non alphanumerics. Docs dont explain this
                # terms = re.sub('[^a-zA-Z0-9]', '', terms)
                chars_to_escape = []

            case IndexSearchType.lnx:
                # https://docs.lnx.rs/#tag/Run-searches/operation/Search_Index_indexes__index__search_post
                # seems ok with any chars, needs testing
                chars_to_escape = []

            case IndexSearchType.typesense:
                # https://typesense.org/docs/26.0/api/search.html#search-parameters
                # seems ok with any chars, needs testing
                chars_to_escape = []
                if not terms:
                    terms = '*' # return all
            
            case _:
                chars_to_escape = []

        for char in chars_to_escape:
            terms = terms.replace(char, '\\' + char) # e.g. @ becomes \@

        q = SearchQuery(
            terms=terms,
            boards=params['boards']
        )
        if params['num']:
            q.num = int(params['num'])
        if params['result_limit']:
            q.result_limit = min(int(params['result_limit']), CONSTS.max_result_limit)
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
        if params['order_by'] in ('asc', 'desc'):
            q.sort = params['order_by']

        parsed_query = perf_counter() - start
        search_log.warning(f'{parsed_query=:.4f}')

        results, total_hits = await search_p.search_posts(q)
        pages = total_pages(total_hits, q.result_limit)
        cur_page = q.page

        got_search = perf_counter() - start
        search_log.warning(f'{got_search=:.4f}')

        hl_re = get_term_re(q.terms) if q.terms else None
        for post in results:
            # post['op'] = post['resto'] == 0
            op_num = post['no'] if post['resto'] == 0 else post['resto']
            if post['comment']:
                if hl_re:
                    post['comment'] = mark_highlight(hl_re, post['comment'])
                _, post['comment'] = restore_comment(op_num, post['comment'], post['board_shortname'])
            posts_t.append(wrap_post_t(post))
        
        patched_posts = perf_counter() - start
        search_log.warning(f'{patched_posts=:.4f}')
        
        res_count = len(results)
        posts_t = ''.join(template_index_post.render(**p) for p in posts_t)
            
        searched = True
        
        if form.search_mode.data == 'gallery':
            search_mode = 'gallery'

    rend_posts = perf_counter() - start
    search_log.warning(f'{rend_posts=:.4f}')

    rend = template_index_search.render(
        search_mode=search_mode,
        form=form,
        posts_t=posts_t,
        res_count=res_count,
        searched=searched,
        quotelinks=quotelinks,
        search_result=True,
        tab_title=CONSTS.site_name,
        cur_page=cur_page,
        pages=pages,
        total_hits=total_hits,
        # **CONSTS.render_constants
    )

    rend_page = perf_counter() - start# - patched_posts
    search_log.warning(f'{rend_page=:.4f}')

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
