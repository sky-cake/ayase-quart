from quart import Blueprint

from asagi_converter import (
    generate_catalog,
    generate_index,
    generate_thread
)
from moderation.filter_cache import fc
from utils.validation import validate_board

from configs import app_conf


bp = Blueprint("bp_api_app", __name__, url_prefix='/api/v1')


if app_conf['api']:
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
