from flask_paginate import Pagination
from quart import Blueprint

from asagi_converter import (
    generate_catalog,
    generate_index,
    generate_thread,
    get_op_thread_count
)
from boards import get_title
from configs import SITE_NAME
from moderation.filter_cache import fc
from posts.template_optimizer import (
    render_catalog_card,
    render_wrapped_post_t,
    report_modal_t,
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

bp = Blueprint("bp_app", __name__)


async def make_pagination_board_index(board_shortname: str, index: dict, page_num: int) -> Pagination:
    op_thread_count = await get_op_thread_count(board_shortname)
    op_thread_removed_count = await fc.get_op_thread_removed_count(board_shortname)
    op_thread_count -= op_thread_removed_count

    board_index_thread_count = len(index['threads'])

    # https://flask-paginate.readthedocs.io/en/master/
    return Pagination(
        page=page_num,
        display_msg=f'Displaying <b>{board_index_thread_count}</b> threads. <b>{op_thread_count}</b> threads in total.',
        total=op_thread_count,
        search=False,
        record_name='threads',
        href=f'/{board_shortname}/page/' + '{0}',
        show_single_page=True,
    )


@bp.get("/")
async def v_index():
    return await render_controller(template_index, tab_title=SITE_NAME)


@bp.get("/<string:board_shortname>")
async def v_board_index(board_shortname: str):
    """See `v_board_index_page()` for benchmarks.
    """
    validate_board(board_shortname)
    p = Perf('index')
    
    index, quotelinks = await generate_index(board_shortname)
    p.check('query')

    index['threads'] = [{'posts': await fc.filter_reported_posts(posts['posts'])} for posts in index['threads']]
    p.check('filter_reported')

    validate_threads(index['threads'])
    p.check('validate')

    pagination = await make_pagination_board_index(board_shortname, index, 0)
    p.check('pagination')

    threads = '<hr>'.join(
        render_thread_stats(thread['posts'][0]) +
        get_posts_t(thread['posts'], quotelinks)
        for thread in index["threads"]
        if thread['posts']
    )
    p.check('post_t')

    rendered = template_board_index.render(
        tab_title=f'/{board_shortname}/ Index',
        pagination=pagination,
        threads=threads,
        board=board_shortname,
        title=get_title(board_shortname),
    )
    p.check('render')
    print(p)
    
    return rendered


@bp.get("/<string:board_shortname>/page/<int:page_num>")
async def v_board_index_page(board_shortname: str, page_num: int):
    """
    Benchmarked with SQLite (local), 150 OPs, 8th gen i7.
    validate: 0.0000
    gen_indx: 0.0374
    val_thrd: 0.0000
    paginate: 0.0156
    rendered: 1.100 +- 0.400

    Benchmarked with MySQL (home server), ~2 million posts. Rendered on a 5700X
    validate: 0.0000
    gen_indx: 1.4598
    val_thrd: 0.0000
    paginate: 0.1702
    rendered: 0.2564
    """
    p = Perf('index page')
    validate_board(board_shortname)
    p.check('validate board')

    index, quotelinks = await generate_index(board_shortname, page_num)
    p.check('generate index')

    index['threads'] = await fc.filter_reported_posts(index['threads'])
    p.check('filter_reported')

    validate_threads(index['threads'])
    p.check('validate thread')

    pagination = await make_pagination_board_index(board_shortname, index, page_num)
    p.check('paginate')

    threads = '<hr>'.join(
        render_thread_stats(thread['posts'][0]) +
        get_posts_t(thread['posts'], quotelinks)
        for thread in index["threads"]
    )
    p.check('post_t')

    title = get_title(board_shortname)
    rendered = template_board_index.render(
        pagination=pagination,
        threads=threads,
        board=board_shortname,
        title=title,
        tab_title=title,
    )
    p.check('rendered')
    print(p)

    return rendered


async def make_pagination_catalog(board_shortname: str, catalog: list[dict], page_num: int) -> Pagination:
    op_thread_count = await get_op_thread_count(board_shortname)
    op_thread_removed_count = await fc.get_op_thread_removed_count(board_shortname)
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
        href=f'/{board_shortname}/catalog/' + '{0}',
        show_single_page=True,
    )


@bp.get("/<string:board_shortname>/catalog")
async def v_catalog(board_shortname: str):
    """
    Benchmarked with SQLite, page 0, 8th gen i7.
    query   : 0.0649
    paginate: 0.0564
    render  : 0.4166

    Benchmarked with SQLite, page 0, 5700X.
    query   : 0.8345
    paginate: 0.1712
    render  : 0.5372
    """
    validate_board(board_shortname)

    p = Perf('catalog')
    catalog = await generate_catalog(board_shortname)
    p.check('query')

    # `nreplies` won't always be correct, but it does not effect paging
    catalog = [page | {'threads': (await fc.filter_reported_posts(page['threads']))} for page in catalog]
    p.check('filter_reported')

    pagination = await make_pagination_catalog(board_shortname, catalog, 0)
    p.check('paginate')

    threads = ''.join(
        render_catalog_card(wrap_post_t(op))
        for batch in catalog
        for op in batch['threads']
    )
    render = template_catalog.render(
        threads=threads,
        pagination=pagination,
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=f"/{board_shortname}/ Catalog",
    )
    p.check('render')
    print(p)

    return render


@bp.get("/<string:board_shortname>/catalog/<int:page_num>")
async def v_catalog_page(board_shortname: str, page_num: int):
    """
    Benchmarked with SQLite, page 129, 5700X.
    query   : 0.8202
    paginate: 0.1734
    render  : 0.5233
    """
    validate_board(board_shortname)

    p = Perf('catalog page')
    catalog = await generate_catalog(board_shortname, page_num)
    p.check('query')

    # `nreplies` won't always be correct, but it does not effect paging
    catalog = [page | {'threads': (await fc.filter_reported_posts(page['threads']))} for page in catalog]
    p.check('filter_reported')

    pagination = await make_pagination_catalog(board_shortname, catalog, page_num)
    p.check('paginate')

    threads = ''.join(
        render_catalog_card(wrap_post_t(op))
        for batch in catalog
        for op in batch['threads']
    )
    render = template_catalog.render(
        threads=threads,
        pagination=pagination,
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=f"/{board_shortname}/ Catalog",
    )
    p.check('render')
    print(p)

    return render


def get_posts_t(posts: list[dict], post_2_quotelinks: dict[int, list[int]]) -> str:
    for post in posts:
        post['quotelinks'] = post_2_quotelinks.get(post['num'], [])
    
    posts_t = ''.join(render_wrapped_post_t(wrap_post_t(p)) for p in posts)
    return posts_t


def get_counts_from_posts(posts: list[dict]) -> tuple[int]:
    """Returns (nreplies, nimages)"""
    nreplies = 0
    nimages = 0
    for post in posts:
        if post.get('op'):
            nreplies = post.get('nreplies', nreplies)
            nimages = post.get('nimages', nimages)
            break
    return nreplies, nimages


@bp.get("/<string:board_shortname>/thread/<int:thread_id>")
async def v_thread(board_shortname: str, thread_id: int):
    """
    Benchmarked with SQLite (local), /ck/ post with 219 comments, 5700X.
    queries : 0.0150
    validate: 0.0000
    posts_t : 0.0293
    rendered: 0.0053

    Benchmarked with MYSQL (home server), /ck/ post with 284 comments, 5700X.
    queries : 1.1000 +- 0.5000
    validate: 0.0000
    posts_t : 0.0274
    rendered: 0.0419
    """
    validate_board(board_shortname)

    p = Perf(topic='thread')
    # use the existing json app function to grab the data
    post_2_quotelinks, thread_dict = await generate_thread(board_shortname, thread_id)
    p.check('queries')

    thread_dict['posts'] = await fc.filter_reported_posts(thread_dict['posts'])
    p.check('filter_reported')

    nreplies, nimages = get_counts_from_posts(thread_dict['posts'])

    validate_threads(thread_dict['posts'])
    p.check('validate')

    posts_t = get_posts_t(thread_dict['posts'], post_2_quotelinks)
    p.check('posts_t')

    title = f"/{board_shortname}/ #{thread_id}"

    render = template_thread.render(
        posts_t=posts_t,
        report_modal_t=report_modal_t,
        nreplies=nreplies,
        nimages=nimages,
        board=board_shortname,
        title=title,
        tab_title=title,
    )
    p.check('rendered')
    print(p)
    return render
