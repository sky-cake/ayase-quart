from quart import Blueprint, jsonify

from asagi_converter import (
    generate_catalog,
    generate_index,
    generate_post,
    generate_thread
)
from moderation.filter_cache import fc
from posts.template_optimizer import wrap_post_t
from templates import template_search_post_t
from utils import Perf
from utils.validation import validate_board

bp = Blueprint("bp_api", __name__)


@bp.get("/<string:board_shortname>/catalog.json")
async def catalog(board_shortname: str):
    validate_board(board_shortname)

    return await generate_catalog(board_shortname)


@bp.get("/<string:board_shortname>/thread/<int:thread_id>.json")
async def thread(board_shortname: str, thread_id: int):

    validate_board(board_shortname)

    post_2_quotelinks, thread_dict = await generate_thread(board_shortname, thread_id)

    thread_dict['posts'] = await fc.filter_reported_posts(thread_dict['posts'])

    return thread_dict


@bp.get("/<string:board_shortname>/<int:page_num>.json")
async def board_index(board_shortname: str, page_num: int):

    validate_board(board_shortname)

    index = await generate_index(board_shortname, page_num, html=False)
    index['threads'] = await fc.filter_reported_posts(index['threads'])
    return index


@bp.get("/<string:board_shortname>/post/<int:post_id>")
async def v_post(board_shortname: str, post_id: int):
    """Called by the client to generate posts not on the page - e.g. when viewing search results.
    """
    validate_board(board_shortname)

    p = Perf("post")
    post_2_quotelinks, post = await generate_post(board_shortname, post_id)
    p.check('query')

    if not post:
        return jsonify()

    is_removed = await fc.is_post_removed(post.board_shortname, post.num)
    p.check('is_post_removed')
    if is_removed:
        return jsonify()

    html_content = template_search_post_t.render(**wrap_post_t(post | dict(quotelinks={})))

    p.check('render')
    print(p)
    return jsonify(html_content=html_content)
