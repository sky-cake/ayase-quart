from quart import Blueprint
from urllib.parse import unquote

from ...asagi_converter import generate_catalog, generate_index, generate_thread
from ...configs import app_conf
from ...moderation import fc
from ...moderation.auth_api import api_usr_authenticated
from ...utils.validation import validate_board_query_parameter

bp = Blueprint("bp_api_app", __name__, url_prefix='/api/v1')


if app_conf['api']:
    @bp.get("/<string:board>/catalog.json")
    @api_usr_authenticated
    @validate_board_query_parameter
    async def catalog(board: str, authenticated: bool):
        catalog = await generate_catalog(board)
        catalog = [page | {'threads': (await fc.filter_reported_posts(page['threads'], is_authority=authenticated))} for page in catalog]
        return catalog


    @bp.get("/<string:board>/thread/<int:thread_id>.json")
    @api_usr_authenticated
    @validate_board_query_parameter
    async def thread(board: str, thread_id: int, authenticated: bool):
        post_2_quotelinks, thread_dict = await generate_thread(board, thread_id)

        thread_dict['posts'] = await fc.filter_reported_posts(thread_dict['posts'], is_authority=authenticated)

        return thread_dict


    @bp.get("/<string:board>/<int:page_num>.json")
    @api_usr_authenticated
    @validate_board_query_parameter
    async def board_index(board: str, page_num: int, authenticated: bool):
        index = await generate_index(board, page_num=page_num)
        index['threads'] = await fc.filter_reported_posts(index['threads'], is_authority=authenticated)
        return index
