
from time import perf_counter

from flask_paginate import Pagination
from quart import Blueprint

from asagi_converter import (
    convert_thread,
    generate_catalog,
    generate_index,
    get_op_thread_count
)
from configs import CONSTS
from posts.template_optimizer import wrap_post_t
from templates import (
    template_board_index,
    template_catalog,
    template_index,
    template_index_search_post_t,
    template_posts,
    template_thread
)
from utils import (
    get_title,
    render_controller,
    validate_board_shortname,
    validate_threads,
    Perf,
)

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
    return await render_controller(template_index, **CONSTS.render_constants, tab_title=CONSTS.site_name)


@blueprint_app.get("/<string:board_shortname>")
async def v_board_index(board_shortname: str):
    """See `v_board_index_page()` for benchmarks.
    """
    validate_board_shortname(board_shortname)

    index = await generate_index(board_shortname, 1)

    validate_threads(index['threads'])

    pagination = await make_pagination_board_index(board_shortname, index, 0)

    return await render_controller(
        template_board_index,
        **CONSTS.render_constants,
        board_index_page=True,
        tab_title=f'/{board_shortname}/ Index',
        pagination=pagination,
        threads=index["threads"],
        quotelinks=[],
        board=board_shortname,
        title=get_title(board_shortname),
    )


@blueprint_app.get("/<string:board_shortname>/page/<int:page_num>")
async def v_board_index_page(board_shortname: str, page_num: int):
    """
    Benchmarked with SQLite, /news/ with 150 OPs, 8th gen i7.
    validate: 0.0000
    gen_indx: 0.0374
    val_thrd: 0.0000
    paginate: 0.0156
    rendered: 1.100 +- 0.400

    Benchmarked with MySQL (9th gen i5), /g/ with ~2 million posts. Rendered on a 5700X
    validate: 0.0000
    gen_indx: 1.4598
    val_thrd: 0.0000
    paginate: 0.1702
    rendered: 0.2564
    """
    i = perf_counter()
    validate_board_shortname(board_shortname)
    f = perf_counter()
    print(f'validate: {f-i:.4f}')

    i = perf_counter()
    index = await generate_index(board_shortname, page_num)
    f = perf_counter()
    print(f'gen_indx: {f-i:.4f}')

    i = perf_counter()
    validate_threads(index['threads'])
    f = perf_counter()
    print(f'val_thrd: {f-i:.4f}')

    i = perf_counter()
    pagination = await make_pagination_board_index(board_shortname, index, page_num)
    f = perf_counter()
    print(f'paginate: {f-i:.4f}')

    i = perf_counter()
    render = await render_controller(
        template_board_index,
        **CONSTS.render_constants,
        pagination=pagination,
        threads=index["threads"],
        quotelinks=[],
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=get_title(board_shortname),
    )
    f = perf_counter()
    print(f'rendered: {f-i:.4f}')
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
    Benchmarked with SQLite, /news/ with 150 OPs, 8th gen i7.
    time_queries: 0.0646
    time_paginate: 0.0160
    time_render: 1.500 +- 0.500 # inconsistent render times
    """
    validate_board_shortname(board_shortname)

    catalog = await generate_catalog(board_shortname, 1)

    time_init = perf_counter()
    pagination = await make_pagination_catalog(board_shortname, catalog, 0)
    time_paginate = perf_counter()
    print(f'time_paginate: {time_paginate - time_init:.4f}')

    render = await render_controller(
        template_catalog,
        **CONSTS.render_constants,
        catalog=catalog,
        pagination=pagination,
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=f"/{board_shortname}/ Catalog",
    )
    time_render = perf_counter()
    print(f'time_render: {time_render - time_paginate:.4f}')

    return render


@blueprint_app.get("/<string:board_shortname>/catalog/<int:page_num>")
async def v_catalog_page(board_shortname: str, page_num: int):
    validate_board_shortname(board_shortname)

    catalog = await generate_catalog(board_shortname, page_num)

    pagination = await make_pagination_catalog(board_shortname, catalog, page_num)

    return await render_controller(
        template_catalog,
        **CONSTS.render_constants,
        catalog=catalog,
        pagination=pagination,
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=f"/{board_shortname}/ Catalog",
    )


def get_posts_t(thread_dict: dict, post_2_quotelinks: None|list[int]=None) -> str:
    posts_t = []
    for post in thread_dict:
        if quotelinks := post_2_quotelinks.get(str(post['no'])):
            post['quotelinks'] = quotelinks
        else:
            post['quotelinks'] = ''

        post['comment'] = post.pop('com')

        posts_t.append(wrap_post_t(post))

    posts_t = ''.join(template_index_search_post_t.render(**p) for p in posts_t)
    return posts_t


@blueprint_app.get("/<string:board_shortname>/thread/<int:thread_id>")
async def v_thread(board_shortname: str, thread_id: int):
    """
    Benchmarked with SQLite, /news/ post with 102 comments, 8th gen i7.
    queries:  0.0703
    validate: 0.0000
    rendered: 0.0070 += 0.003
    """
    validate_board_shortname(board_shortname)

    p = Perf()
    # use the existing json app function to grab the data
    thread_dict, post_2_quotelinks = await convert_thread(board_shortname, thread_id)
    p.check('queries')

    validate_threads(thread_dict['posts'])
    p.check('validate')

    posts_t = get_posts_t(thread_dict['posts'], post_2_quotelinks=post_2_quotelinks)
    p.check('posts_t')

    title = f"/{board_shortname}/ #{thread_id}"

    render = await render_controller(
        template_thread,
        posts_t=posts_t,
        **CONSTS.render_constants,
        board=board_shortname,
        title=title,
        tab_title=title,
    )
    p.check('rendered')
    return render


@blueprint_app.get("/<string:board_shortname>/posts/<int:thread_id>")
async def v_posts(board_shortname: str, thread_id: int):

    validate_board_shortname(board_shortname)

    thread_dict, quotelinks = await convert_thread(board_shortname, thread_id)

    validate_threads(thread_dict['posts'])

    # remove OP post
    del thread_dict["posts"][0]

    return await render_controller(
        template_posts,
        **CONSTS.render_constants,
        posts=thread_dict["posts"],
        quotelinks=quotelinks,
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=get_title(board_shortname),
    )
