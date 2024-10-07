from flask_paginate import Pagination
from quart import Blueprint

from asagi_converter import (
    generate_catalog,
    generate_index,
    generate_thread,
    get_op_thread_count
)
from configs import SITE_NAME
from posts.template_optimizer import wrap_post_t
from render import get_title, render_controller
from templates import (
    template_board_index,
    template_catalog,
    template_index,
    template_index_search_post_t,
    template_thread
)
from utils import Perf
from utils.validation import validate_threads, validate_board

blueprint_app = Blueprint("blueprint_app", __name__)


async def make_pagination_board_index(board_shortname, index, page_num):
    op_thread_count = await get_op_thread_count(board_shortname)

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

@blueprint_app.get("/")
async def v_index():
    return await render_controller(template_index, tab_title=SITE_NAME)


@blueprint_app.get("/<string:board_shortname>")
async def v_board_index(board_shortname: str):
    """See `v_board_index_page()` for benchmarks.
    """
    validate_board(board_shortname)
    p = Perf('index')
    
    index, quotelinks = await generate_index(board_shortname)
    p.check('query')
    
    validate_threads(index['threads'])
    p.check('validate')

    pagination = await make_pagination_board_index(board_shortname, index, 0)
    p.check('pagination')

    rendered = await render_controller(
        template_board_index,
        board_index_page=True,
        tab_title=f'/{board_shortname}/ Index',
        pagination=pagination,
        threads=index["threads"],
        quotelinks=quotelinks,
        board=board_shortname,
        title=get_title(board_shortname),
    )
    p.check('render')
    print(p)
    
    return rendered


@blueprint_app.get("/<string:board_shortname>/page/<int:page_num>")
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

    validate_threads(index['threads'])
    p.check('validate thread')

    pagination = await make_pagination_board_index(board_shortname, index, page_num)
    p.check('paginate')

    render = await render_controller(
        template_board_index,
        pagination=pagination,
        threads=index["threads"],
        quotelinks=quotelinks,
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=get_title(board_shortname),
    )
    p.check('rendered')
    print(p)

    return render


async def make_pagination_catalog(board_shortname, catalog, page_num):
    op_thread_count = await get_op_thread_count(board_shortname)
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


@blueprint_app.get("/<string:board_shortname>/catalog")
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

    pagination = await make_pagination_catalog(board_shortname, catalog, 0)
    p.check('paginate')

    render = await render_controller(
        template_catalog,
        catalog=catalog,
        pagination=pagination,
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=f"/{board_shortname}/ Catalog",
    )
    p.check('render')
    print(p)

    return render


@blueprint_app.get("/<string:board_shortname>/catalog/<int:page_num>")
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

    pagination = await make_pagination_catalog(board_shortname, catalog, page_num)
    p.check('paginate')

    render = await render_controller(
        template_catalog,
        catalog=catalog,
        pagination=pagination,
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=f"/{board_shortname}/ Catalog",
    )
    p.check('render')
    print(p)

    return render


def get_posts_t(thread_dict: dict, post_2_quotelinks: dict[int, list[int]]) -> str:
    posts_t = []
    for post in thread_dict:
        post['quotelinks'] = post_2_quotelinks.get(post['num'], [])
        posts_t.append(wrap_post_t(post))

    posts_t = ''.join(template_index_search_post_t.render(**p) for p in posts_t)
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


@blueprint_app.get("/<string:board_shortname>/thread/<int:thread_id>")
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

    nreplies, nimages = get_counts_from_posts(thread_dict['posts'])

    validate_threads(thread_dict['posts'])
    p.check('validate')

    posts_t = get_posts_t(thread_dict['posts'], post_2_quotelinks)
    p.check('posts_t')

    title = f"/{board_shortname}/ #{thread_id}"

    render = await render_controller(
        template_thread,
        posts_t=posts_t,
        nreplies=nreplies,
        nimages=nimages,
        board=board_shortname,
        title=title,
        tab_title=title,
    )
    p.check('rendered')
    print(p)
    return render
