from quart import request
from werkzeug.exceptions import BadRequest, MethodNotAllowed

from asagi_converter import (
    html_comment,
    search_posts,
    search_posts_get_thread_nums
)
from configs import SITE_NAME, index_search_conf, vanilla_search_conf
from enums import SearchType
from forms import IndexSearchForm, VanillaSearchForm
from moderation.filter_cache import fc
from posts.template_optimizer import (
    get_gallery_media_t,
    report_modal_t,
    wrap_post_t
)
from search.highlighting import highlight_search_results
from search.pagination import template_pagination_links, total_pages
from search.providers import get_index_search_provider
from search.query import get_index_search_query
from templates import (
    template_search,
    template_search_gallery_post_t,
    template_search_post_t
)
from utils import Perf


async def get_posts_and_total_hits(search_type: SearchType, form_data: dict, p: Perf) -> tuple[list[dict], int]:
    if search_type == SearchType.idx:
        query = get_index_search_query(form_data)
        p.check('parsed query')
        return await get_index_search_provider().search_posts(query)

    return await search_posts(form_data)


async def get_posts_and_total_hits_faceted(search_type: SearchType, form_data: dict, p: Perf) -> tuple[list[dict], int]:

    if search_type == SearchType.idx:
        query = get_index_search_query(form_data)
        p.check('parsed facet query')
        board_2_op_nums = await get_index_search_provider().search_posts_get_thread_nums(query, form_data)

    elif search_type == SearchType.sql:
        board_2_op_nums = await search_posts_get_thread_nums(form_data)

    else:
        raise ValueError(search_type)

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
    if search_type == SearchType.idx and not index_search_conf.get('enabled'):
        raise BadRequest('index search is disabled')

    if search_type == SearchType.sql and not vanilla_search_conf.get('enabled'):
        raise BadRequest('vanilla search is disabled')

    if search_type == SearchType.idx:
        highlight_enabled = index_search_conf.get('highlight')
        search_form = IndexSearchForm
    elif search_type == SearchType.sql:
        highlight_enabled = vanilla_search_conf.get('highlight')
        search_form = VanillaSearchForm
    else:
        raise ValueError(search_type)

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
        form: VanillaSearchForm = await search_form.create_form(meta={'csrf': False})
    elif request.method == 'GET':
        boards = request.args.getlist('boards')
        params = {**request.args}
        params['boards'] = boards
        form: VanillaSearchForm = await search_form.create_form(meta={'csrf': False}, **params)
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
                hl_search_term_comment = form.comment.data if highlight_enabled and form.comment.data else None
                hl_search_term_title = form.title.data if highlight_enabled and form.title.data else None

                post['comment'] = html_comment(post['comment'], post['op_num'], post['board_shortname'], highlight=True)

                post['comment'] = highlight_search_results(post['comment'], hl_search_term_comment, is_comment=True)
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