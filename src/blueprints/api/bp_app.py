from quart import Blueprint

from asagi_converter import generate_catalog, generate_index, generate_thread
from configs import app_conf
from moderation import fc
from moderation.auth import api_usr_authenticated
from utils.validation import validate_board

bp = Blueprint("bp_api_app", __name__, url_prefix='/api/v1')


if app_conf['api']:
    @bp.get("/<string:board>/catalog.json")
    @api_usr_authenticated
    async def catalog(board: str, authenticated: bool):
        validate_board(board)

        catalog = await generate_catalog(board)
        catalog = [page | {'threads': (await fc.filter_reported_posts(page['threads'], is_authority=authenticated))} for page in catalog]
        return catalog


    @bp.get("/<string:board>/thread/<int:thread_id>.json")
    @api_usr_authenticated
    async def thread(board: str, thread_id: int, authenticated: bool):

        validate_board(board)

        post_2_quotelinks, thread_dict = await generate_thread(board, thread_id)

        thread_dict['posts'] = await fc.filter_reported_posts(thread_dict['posts'], is_authority=authenticated)

        return thread_dict


    @bp.get("/<string:board>/<int:page_num>.json")
    @api_usr_authenticated
    async def board_index(board: str, page_num: int, authenticated: bool):

        validate_board(board)

        index = await generate_index(board, page_num, html=False)
        index['threads'] = await fc.filter_reported_posts(index['threads'], is_authority=authenticated)
        return index
