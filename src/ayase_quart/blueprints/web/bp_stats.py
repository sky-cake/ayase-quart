from quart import Blueprint, Response

from ...asagi_converter import get_post_counts_per_month_by_board
from ...boards import board_objects
from ...moderation.auth import (
    load_web_usr_data,
    web_usr_is_admin,
    web_usr_logged_in
)
from ...render import render_controller
from ...templates import template_stats
from ...utils.validation import validate_board

bp = Blueprint('bp_web_stats', __name__)


@bp.get("/stats/<string:board>")
async def stats_board(board: str):
    validate_board(board)
    post_counts_per_month_by_board = await get_post_counts_per_month_by_board(board)
    return Response(post_counts_per_month_by_board, content_type='application/json')


@bp.route("/stats")
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def v_stats(logged_in: bool, is_admin: bool):
    return await render_controller(
        template_stats,
        board_objects=board_objects,
        logo_filename='logo.png',
        title='Stats',
        tab_title='Stats',
        logged_in=logged_in,
        is_admin=is_admin,
    )
