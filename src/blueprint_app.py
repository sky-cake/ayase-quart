import quart_flask_patch # keep this here

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
    template_search,
    template_latest_gallery
)
from configs import CONSTS
from utils import render_controller, validate_board_shortname, validate_threads, get_title
from quart import Blueprint
from flask_paginate import Pagination
from forms import SearchForm
from werkzeug.exceptions import BadRequest
from utils import highlight_search_results

blueprint_app = Blueprint("blueprint_app", __name__, template_folder="templates")


@blueprint_app.errorhandler(404)
async def error_not_found(e):
    return await render_controller(
        template_error_404,
        message='404 Not Found',
        **CONSTS.render_constants,
        tab_title=f'Error'
    )


@blueprint_app.errorhandler(400)
async def error_invalid(e):
    return await render_controller(
        template_error_404,
        e=e.description,
        message='The search parameters will result in 0 records.',
        **CONSTS.render_constants,
        tab_title=f'Invalid search'
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

        if form.search_mode.data not in ['index', 'gallery']: raise BadRequest('search mode is unknown')
        if form.is_op.data and form.is_not_op.data: raise BadRequest('is_op is contradicted')
        if form.is_deleted.data and form.is_not_deleted.data: raise BadRequest('is_deleted is contradicted')
        if form.has_file.data and form.has_no_file.data: raise BadRequest('has_file is contradicted')
        if form.date_before.data and form.date_after.data and (form.date_before.data < form.date_after.data): raise BadRequest('the dates are contradicted')

        params = form.data
        
        posts, quotelinks = await get_posts_filtered(params, form.result_limit.data) # posts = {'posts': [{...}, {...}, ...]}

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
        board_index_page=True,
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
    validate_threads(thread_dict['posts'])

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
