
from logging import getLogger

from quart import Blueprint, request
from werkzeug.exceptions import BadRequest, MethodNotAllowed

from asagi_converter import (
    search_posts,
    html_highlight,
    restore_comment,
)
from boards import board_shortnames
from configs import SITE_NAME
from enums import SearchResultMode, SearchType
from forms import SearchForm
from posts.template_optimizer import get_gallery_media_t, wrap_post_t
from render import render_controller
from search import HIGHLIGHT_ENABLED, MAX_RESULTS_LIMIT, SEARCH_ENABLED
from search.highlighting import get_term_re, mark_highlight
from search.pagination import template_pagination_links, total_pages
from search.providers import get_search_provider
from search.query import get_search_query
from templates import (
    template_error_404,
    template_index_search,
    template_index_search_config,
    template_index_search_gallery_post_t,
    template_index_search_post_t,
)
from utils import Perf
from utils.validation import positive_int

search_log = getLogger('search')

bp = Blueprint("bp_search", __name__)


@bp.route("/index_search_config", methods=['GET', 'POST'])
async def index_search_config():
    return await render_controller(
        template_index_search_config,
        tab_title=SITE_NAME,
        board_list=' '.join(board_shortnames),
    )


@bp.route("/index_stats", methods=['GET'])
async def index_search_stats():
    search_p = get_search_provider()
    return await search_p.post_stats()


@bp.errorhandler(404)
async def error_not_found(e):
    return await render_controller(template_error_404, message='404 Not Found', tab_title=f'Error')


@bp.errorhandler(400)
async def error_invalid(e):
    return await render_controller(
        template_error_404, e=e.description, message='The search parameters will result in 0 records.', tab_title=f'Invalid search'
    )


async def search_handler(search_type: SearchType) -> str:
    if not SEARCH_ENABLED:
        raise BadRequest('search is disabled')

    search_result_mode = SearchResultMode.index
    searched = False
    cur_page = None
    pages = None
    total_hits = None
    posts_t = []
    posts = []
    quotelinks = []
    page_links = ''

    p = Perf(f'{search_type.value} search')

    if request.method == 'POST':
        form: SearchForm = await SearchForm.create_form(meta={'csrf': False})
    elif request.method == 'GET':
        boards = request.args.getlist('boards')
        params = {**request.args}
        params['boards'] = boards
        form: SearchForm = await SearchForm.create_form(meta={'csrf': False}, **params)
    else:
        raise MethodNotAllowed()

    is_search_request = bool(form.boards.data) and form.submit.data

    if is_search_request and (await form.validate()):
        searched = True
        if form.search_mode.data == SearchResultMode.gallery:
            search_result_mode = SearchResultMode.gallery
            form.has_file.data = True
            form.has_no_file.data = False

        query = get_search_query(form.data)
        p.check('parsed query')

        query.page = positive_int(form.page.data, lower=1)
        cur_page = query.page
        per_page = positive_int(query.result_limit, 1, MAX_RESULTS_LIMIT)

        if search_type == SearchType.idx:
            search_p = get_search_provider()
            posts, total_hits = await search_p.search_posts(query)
            p.check('search done')

            pages = total_pages(total_hits, per_page)
            cur_page = positive_int(cur_page, 1, pages)
            endpoint_path = '/index_search'

            if search_result_mode == SearchResultMode.index:
                hl_re = get_term_re(query.terms) if HIGHLIGHT_ENABLED and query.terms else None
                for post in posts:
                    if post['comment']:
                        if hl_re:
                            post['comment'] = mark_highlight(hl_re, post['comment'])
                        _, post['comment'] = restore_comment(post['op_num'], post['comment'], post['board_shortname'])

                    posts_t.append(wrap_post_t(post))

        else:
            posts, total_hits = await search_posts(form.data, form.result_limit.data, form.order_by.data)
            p.check('search done')

            pages = total_pages(total_hits, per_page)
            cur_page = positive_int(cur_page, 1, pages)
            endpoint_path = '/search'

            posts = posts[((cur_page-1) * per_page):((cur_page-1) * per_page) + per_page] # TODO: offload paging to db

            if search_result_mode == SearchResultMode.index:
                hl_re_comment = get_term_re(form.comment.data) if HIGHLIGHT_ENABLED and form.comment.data else None
                hl_re_title = get_term_re(form.title.data) if HIGHLIGHT_ENABLED and form.title.data else None

                for post in posts:
                    if post['comment'] and hl_re_comment:
                        post['comment'] = html_highlight(mark_highlight(hl_re_comment, post['comment']))

                    if post['title'] and hl_re_title:
                        post['title'] = html_highlight(mark_highlight(hl_re_title, post['title']), magenta=False)

                    posts_t.append(wrap_post_t(post))

        page_links = template_pagination_links(endpoint_path, form.data, pages, cur_page)
        p.check('patched posts')

        if search_result_mode == SearchResultMode.index:
            posts_t = ''.join(template_index_search_post_t.render(**p) for p in posts_t)
        else:
            posts_t = ''.join(template_index_search_gallery_post_t.render(post=post, t_gallery_media=get_gallery_media_t(post)) for post in posts)

        p.check('rendered posts')

    rendered_page = template_index_search.render(
        search_mode=search_result_mode,
        form=form,
        posts_t=posts_t,
        page_links=page_links,
        res_count=len(posts),
        searched=searched,
        quotelinks=quotelinks,
        search_result=True,
        tab_title=SITE_NAME,
        cur_page=cur_page,
        pages=pages,
        total_hits=total_hits,
    )

    p.check('rendered page')
    print(p)

    return rendered_page


@bp.route("/index_search", methods=['GET', 'POST'])
async def v_index_search():
    return await search_handler(SearchType.idx)


@bp.route("/search", methods=['GET', 'POST'])
async def v_search():
    return await search_handler(SearchType.sql)
