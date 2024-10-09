
from logging import getLogger

from quart import Blueprint, request
from werkzeug.exceptions import BadRequest

from asagi_converter import (
    get_posts_filtered,
    get_posts_filtered2,
    restore_comment
)
from boards import board_shortnames
from configs import SITE_NAME
from enums import SearchMode
from forms import SearchForm
from posts.template_optimizer import get_gallery_media_t, wrap_post_t
from render import render_controller
from search import HIGHLIGHT_ENABLED, SEARCH_ENABLED
from search.highlighting import (
    get_term_re,
    highlight_search_results,
    mark_highlight
)
from search.pagination import template_pagination_links, total_pages
from search.providers import get_search_provider
from search.query import get_search_query
from templates import (
    template_error_404,
    template_index_search,
    template_index_search_config,
    template_index_search_gallery_post_t,
    template_index_search_post_t,
    template_search
)
from utils import Perf
from utils.validation import validate_board

search_log = getLogger('search')

blueprint_search = Blueprint("blueprint_search", __name__)


@blueprint_search.route("/index_search_config", methods=['GET', 'POST'])
async def index_search_config():
    return await render_controller(
        template_index_search_config,
        tab_title=SITE_NAME,
        board_list=' '.join(board_shortnames),
    )


@blueprint_search.route("/index_stats", methods=['GET'])
async def index_search_stats():
    search_p = get_search_provider()
    return await search_p.post_stats()


@blueprint_search.errorhandler(404)
async def error_not_found(e):
    return await render_controller(template_error_404, message='404 Not Found', tab_title=f'Error')


@blueprint_search.errorhandler(400)
async def error_invalid(e):
    return await render_controller(
        template_error_404, e=e.description, message='The search parameters will result in 0 records.', tab_title=f'Invalid search'
    )


@blueprint_search.route("/index_search", methods=['GET', 'POST'])
async def v_index_search():
    if not SEARCH_ENABLED:
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
    p = Perf('index search')
    search_p = get_search_provider()

    if request.method == 'POST':
        form: SearchForm = await SearchForm.create_form(meta={'csrf': False})
    else:
        boards = request.args.getlist('boards')
        params = {**request.args}
        params['boards'] = boards
        form: SearchForm = await SearchForm.create_form(meta={'csrf': False}, **params)

    if (await form.validate_on_submit()):
        searched = True
        if form.search_mode.data == SearchMode.gallery:
            search_mode = SearchMode.gallery

        q = get_search_query(form.data)

        p.check('parsed query')

        results, total_hits = await search_p.search_posts(q)
        pages = total_pages(total_hits, q.result_limit)
        cur_page = q.page
        page_links = template_pagination_links('/index_search', form.data, pages, cur_page)

        p.check('search done')

        if search_mode == SearchMode.index:
            hl_re = get_term_re(q.terms) if q.terms else None
            for post in results:
                if post['comment']:
                    if hl_re:
                        post['comment'] = mark_highlight(hl_re, post['comment'])
                    _, post['comment'] = restore_comment(post['op_num'], post['comment'], post['board_shortname'])

                posts_t.append(wrap_post_t(post))

        p.check('patch posts')

        if search_mode == SearchMode.index:
            posts_t = ''.join(template_index_search_post_t.render(**p) for p in posts_t)
        else:
            posts_t = ''.join(template_index_search_gallery_post_t.render(post=post, t_gallery_media=get_gallery_media_t(post)) for post in results)

        p.check('render posts')

    rend = template_index_search.render(
        search_mode=search_mode,
        form=form,
        posts_t=posts_t,
        page_links=page_links,
        res_count=len(results),
        searched=searched,
        quotelinks=quotelinks,
        search_result=True,
        tab_title=SITE_NAME,
        cur_page=cur_page,
        pages=pages,
        total_hits=total_hits,
    )

    p.check('render page')
    print(p)

    return rend


@blueprint_search.route("/search", methods=['GET', 'POST'])
async def v_search():
    if not SEARCH_ENABLED:
        raise BadRequest('search is disabled')

    form = await SearchForm.create_form(meta={'csrf': False})
    search_mode = SearchMode.index
    searched = False

    posts = []
    quotelinks = []
    p = Perf()

    if (await form.validate_on_submit()):
        searched = True
        p.check('validate')

        # posts is {'posts': [{...}, {...}, ...]}
        # posts, quotelinks = await get_posts_filtered(form.data, form.result_limit.data, form.order_by.data)
        posts, quotelinks = await get_posts_filtered2(form.data, form.result_limit.data, form.order_by.data)
        p.check('query')

        if HIGHLIGHT_ENABLED:
            posts = highlight_search_results(form, posts)
        p.check('highlight')

        posts = posts['posts']

        if form.search_mode.data == SearchMode.gallery:
            search_mode = SearchMode.gallery
    
    rendered = await render_controller(
        template_search,
        search_mode=search_mode,
        form=form,
        posts=posts,
        searched=searched,
        quotelinks=quotelinks,
        search_result=True,
        tab_title=SITE_NAME,
    )
    p.check('render')
    print(p)
    
    return rendered
