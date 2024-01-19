from asagi_converter import (
    convert_thread,
    generate_index,
    convert_post,
    generate_catalog
)

from templates import (
    template_post
)
from configs import CONSTS
from utils import render_controller, validate_board_shortname, validate_post
from quart import Blueprint, jsonify


blueprint_api = Blueprint("blueprint_api", __name__, template_folder="templates")


@blueprint_api.get("/<string:board_shortname>/catalog.json")
async def catalog(board_shortname: str):
    validate_board_shortname(board_shortname)

    return await generate_catalog(board_shortname, 1)


@blueprint_api.get("/<string:board_shortname>/thread/<int:thread_id>.json")
async def thread(board_shortname: str, thread_id: int):

    validate_board_shortname(board_shortname)

    res = await convert_thread(board_shortname, thread_id)

    if res and len(res) > 0 and res[0].get("posts", False):
        return res


@blueprint_api.get("/<string:board_shortname>/<int:page_num>.json")
async def board_index(board_shortname: str, page_num: int):
    
    validate_board_shortname(board_shortname)

    res = await generate_index(board_shortname, page_num, html=False)
    if res and res.get("threads"):
        return res


@blueprint_api.get("/<string:board_shortname>/post/<int:post_id>")
async def v_post(board_shortname: str, post_id: int):
    """Called by the client to generate posts not on the page - e.g. when viewing search results."""

    validate_board_shortname(board_shortname)

    post, quotelinks = await convert_post(board_shortname, post_id)
    post = post[0]
    validate_post(post)

    html_content = await render_controller(
        template_post, 
        **CONSTS.render_constants,
        post=post,
        board=board_shortname,
        quotelink=quotelinks
    )
    return jsonify(html_content=html_content)
