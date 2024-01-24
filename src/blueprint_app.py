import quart_flask_patch

from asagi_converter import (
    convert_thread,
    generate_index,
    generate_catalog,
    get_op_thread_count,
    get_posts_filtered
)

from templates import (
    template_board_index,
    template_catalog,
    template_index,
    template_posts,
    template_thread,
    template_error_404,
    template_search
)
from configs import CONSTS
from utils import render_controller, validate_board_shortname, validate_threads, get_title
from quart import Blueprint
from flask_paginate import Pagination
from forms import SearchForm
from werkzeug.exceptions import NotFound
from utils import highlight_search_results

blueprint_app = Blueprint("blueprint_app", __name__, template_folder="templates")


@blueprint_app.errorhandler(404)
async def error_not_found(e):
    return await render_controller(
        template_error_404,
        **CONSTS.render_constants,
        tab_title=f'Error!'
    )


@blueprint_app.get("/")
async def v_index():
    return await render_controller(
        template_index,
        **CONSTS.render_constants,
        tab_title=CONSTS.site_name
    )


@blueprint_app.route("/search", methods=['GET', 'POST'])
async def v_search():
    if not CONSTS.search:
        raise NotFound
    
    form = await SearchForm.create_form()

    posts = []
    quotelinks = []
    if await form.validate_on_submit():

        for board in form.boards.data:
            validate_board_shortname(board)

        if form.is_op.data and form.is_not_op.data: raise NotFound
        if form.has_file.data and form.has_no_file.data: raise NotFound
        if form.date_before.data and form.date_after.data and (form.date_before.data < form.date_after.data): raise NotFound

        params = form.data
        
        posts, quotelinks = await get_posts_filtered(params) # posts = {'posts': [{...}, {...}, ...]}

        if CONSTS.search_result_highlight:
            posts = highlight_search_results(form, posts)
            
        posts = posts['posts']
        
    return await render_controller(
        template_search,
        form=form,
        posts=posts,
        quotelinks=quotelinks,
        search_result=True,
        search_result_limit=CONSTS.search_result_limit,
        tab_title=CONSTS.site_name,
        **CONSTS.render_constants
    )


async def make_pagination_board_index(board_shortname, index, page_num):
    op_thread_count = await get_op_thread_count(board_shortname)
    index_pages = int(op_thread_count / 10) # we grab 10 OPs per index page

    board_index_thread_count = len(index['threads'])

    # https://flask-paginate.readthedocs.io/en/master/
    return Pagination(
        page=page_num,
        display_msg=f'Displaying <b>{board_index_thread_count}</b> threads. <b>{op_thread_count}</b> threads in total.',
        total=op_thread_count,
        search=False,
        record_name='threads',
        href=f'/{board_shortname}/page/' + '{0}',
        show_single_page=True
    )


@blueprint_app.get("/<string:board_shortname>")
async def v_board_index(board_shortname: str):
    validate_board_shortname(board_shortname)
    
    index = await generate_index(board_shortname, 1)

    validate_threads(index['threads'])

    pagination = await make_pagination_board_index(board_shortname, index, 0)

    return await render_controller(
        template_board_index, 
        **CONSTS.render_constants,
        tab_title=f'/{board_shortname}/ Index',
        pagination=pagination,
        threads=index["threads"],
        quotelinks=[],
        board=board_shortname,
        title=get_title(board_shortname)
    )


@blueprint_app.get("/<string:board_shortname>/page/<int:page_num>")
async def v_board_index_page(board_shortname: str, page_num: int):

    validate_board_shortname(board_shortname)

    index = await generate_index(board_shortname, page_num)

    validate_threads(index['threads'])

    pagination = await make_pagination_board_index(board_shortname, index, page_num)

    return await render_controller(
        template_board_index, 
        **CONSTS.render_constants,
        pagination = pagination,
        threads=index["threads"],
        quotelinks=[],
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=get_title(board_shortname)
    )


async def make_pagination_catalog(board_shortname, catalog, page_num):
    op_thread_count = await get_op_thread_count(board_shortname)
    catalog_pages = int(op_thread_count / 15) + 1 # we grab 150 threads per catalog page

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
        show_single_page=True
    )

@blueprint_app.get("/<string:board_shortname>/catalog")
async def v_catalog(board_shortname: str):

    validate_board_shortname(board_shortname)

    catalog = await generate_catalog(board_shortname, 1)

    pagination = await make_pagination_catalog(board_shortname, catalog, 0)

    return await render_controller(
        template_catalog, 
        **CONSTS.render_constants,
        catalog=catalog,
        pagination=pagination,
        board=board_shortname,
        title=get_title(board_shortname),
        tab_title=f"/{board_shortname}/ Catalog"
    )


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
        tab_title=f"/{board_shortname}/ Catalog"
    )


@blueprint_app.get("/<string:board_shortname>/thread/<int:thread_id>")
async def v_thread(board_shortname: str, thread_id: int):
    validate_board_shortname(board_shortname)
    
    # use the existing json app function to grab the data
    thread_dict, quotelinks = await convert_thread(board_shortname, thread_id)

    title = f"/{board_shortname}/ #{thread_id}"

    return await render_controller(
        template_thread, 
        **CONSTS.render_constants,
        posts=thread_dict["posts"],
        quotelinks=quotelinks,
        board=board_shortname,
        title=title,
        tab_title=title,
    )


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
