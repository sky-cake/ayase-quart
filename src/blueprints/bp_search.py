
from logging import getLogger

from quart import Blueprint, request
from werkzeug.exceptions import BadRequest, MethodNotAllowed

from asagi_converter import (
    restore_comment,
    search_posts,
    search_posts_get_thread_nums
)
from boards import board_shortnames
from configs import SITE_NAME
from enums import SearchType
from forms import SearchForm
from moderation.filter_cache import fc
from posts.template_optimizer import (
    get_gallery_media_t,
    report_modal_t,
    wrap_post_t
)
from render import render_controller
from search import HIGHLIGHT_ENABLED, SEARCH_ENABLED
from search.highlighting import highlight_search_results
from search.pagination import template_pagination_links, total_pages
from search.providers import get_search_provider
from search.query import get_search_query
from templates import (
    template_search,
    template_search_gallery_post_t,
    template_search_info,
    template_search_post_t
)
from utils import Perf

search_log = getLogger('search')

bp = Blueprint("bp_search", __name__)


@bp.route("/index_search_config", methods=['GET', 'POST'])
async def index_search_config():
    return await render_controller(
        template_search_info,
        title=SITE_NAME,
        tab_title=SITE_NAME,
        board_list=' '.join(board_shortnames),
    )


@bp.route("/index_stats", methods=['GET'])
async def index_search_stats():
    search_p = get_search_provider()
    return await search_p.post_stats()


async def get_posts_and_total_hits(search_type: SearchType, form_data: dict, p: Perf) -> tuple[list[dict], int]:
    if search_type == SearchType.idx:
        query = get_search_query(form_data)
        p.check('parsed query')
        return await get_search_provider().search_posts(query)

    return await search_posts(form_data)


async def get_posts_and_total_hits_faceted(search_type: SearchType, form_data: dict, p: Perf) -> tuple[list[dict], int]:
    query = get_search_query(form_data)
    p.check('parsed facet query')

    if search_type == SearchType.idx:
        board_2_op_nums = await get_search_provider().search_posts_get_thread_nums(query, form_data)
    else:
        board_2_op_nums = await search_posts_get_thread_nums(form_data)

    p.check('facet search done')

    posts = []
    total_hits = 0
    for board, op_nums in board_2_op_nums.items():
        # must go one board at a time to maintain board:op_num integrity
        # if we want, we can limit faceted search to 1 board in the form validation
        form_data['boards'] = [board]
        form_data['thread_nums'] = op_nums
        _posts, _total_hits = await get_posts_and_total_hits(search_type, form_data, p)
        posts.extend(_posts)
        total_hits += _total_hits
        p.check(f'f-search done on {board}')

    return posts, total_hits


async def search_handler(search_type: SearchType) -> str:
    if not SEARCH_ENABLED:
        raise BadRequest('search is disabled')

    gallery_mode = False
    searched = False
    cur_page = 1
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
        if form.gallery_mode.data:
            gallery_mode = True

        form_data = form.data

        is_facet_search = bool(form_data['op_title'] or form_data['op_comment'])
        if is_facet_search:
            posts, total_hits = await get_posts_and_total_hits_faceted(search_type, form_data, p)
        else:
            posts, total_hits = await get_posts_and_total_hits(search_type, form_data, p)

        p.check('search done')

        posts = await fc.filter_reported_posts(posts)
        p.check('filter_reported')

        if not gallery_mode:
            for post in posts:
                hl_search_term_comment = form.comment.data if HIGHLIGHT_ENABLED and form.comment.data else None
                hl_search_term_title = form.title.data if HIGHLIGHT_ENABLED and form.title.data else None

                _, post['comment'] = restore_comment(post['op_num'], post['comment'], post['board_shortname'], hl_search_term=hl_search_term_comment)
                post['title'] = highlight_search_results(post['title'], hl_search_term_title, is_comment=False)

                posts_t.append(wrap_post_t(post))

            posts_t = ''.join(template_search_post_t.render(**p) for p in posts_t)

        else:
            # doesn't require restored comments because it's just a gallery
            posts_t = ''.join(template_search_gallery_post_t.render(post=post, t_gallery_media=get_gallery_media_t(post)) for post in posts)
        
        p.check('templated posts')

        endpoint_path = '/index_search' if search_type == SearchType.idx else '/search'
        pages = total_pages(total_hits, form_data['hits_per_page'])
        page_links = template_pagination_links(endpoint_path, form_data, pages)

        p.check('templated links')
        cur_page = form_data.get('page', cur_page)

    rendered_page = template_search.render(
        gallery_mode=gallery_mode,
        form=form,
        posts_t=posts_t,
        report_modal_t=report_modal_t,
        page_links=page_links,
        result_count=len(posts),
        searched=searched,
        quotelinks=quotelinks,
        search_result=True,
        tab_title=SITE_NAME,
        title=f'{SITE_NAME} Search',
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
