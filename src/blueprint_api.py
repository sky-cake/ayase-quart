from quart import Blueprint, jsonify, url_for

from asagi_converter import (
    generate_catalog,
    generate_index,
    generate_post,
    generate_thread
)
from configs import CONSTS
from render import render_controller, validate_board_shortname
from templates import template_post
from utils import Perf, validate_post

blueprint_api = Blueprint("blueprint_api", __name__)


@blueprint_api.get("/<string:board_shortname>/catalog.json")
async def catalog(board_shortname: str):
    validate_board_shortname(board_shortname)

    return await generate_catalog(board_shortname, 1)


@blueprint_api.get("/<string:board_shortname>/thread/<int:thread_id>.json")
async def thread(board_shortname: str, thread_id: int):

    validate_board_shortname(board_shortname)

    post_2_quotelinks, results = await generate_thread(board_shortname, thread_id)

    if results and len(results) > 0 and results[0].get("posts", False):
        return results


@blueprint_api.get("/<string:board_shortname>/<int:page_num>.json")
async def board_index(board_shortname: str, page_num: int):

    validate_board_shortname(board_shortname)

    res = await generate_index(board_shortname, page_num, html=False)
    if res and res.get("threads"):
        return res


@blueprint_api.get("/<string:board_shortname>/post/<int:post_id>")
async def v_post(board_shortname: str, post_id: int):
    """Called by the client to generate posts not on the page - e.g. when viewing search results.

    MYSQL
    query: 0.6046
    rendr: 0.0096

    SQLITE
    query: 0.0020
    rendr: 0.0103
    """
    validate_board_shortname(board_shortname)

    p = Perf()
    post_2_quotelinks, post = await generate_post(board_shortname, post_id)
    p.check('query')
    validate_post(post)

    html_content = await render_controller(template_post, **CONSTS.render_constants, post=post, board=board_shortname, quotelinks=post_2_quotelinks)
    p.check('rendr')
    return jsonify(html_content=html_content)
