import quart_flask_patch

from quart import Blueprint
from asagi_converter import get_row_counts
from boards import board_objects
from moderation.auth import (
    load_web_usr_data,
    web_usr_logged_in,
    web_usr_is_admin,
)
from render import render_controller
from utils.validation import validate_board
from templates import (
    template_stats,
    template_stats_board,
)


bp = Blueprint('bp_web_stats', __name__)


@bp.route("/stats/<string:board>")
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def stats_board(logged_in: bool, is_admin: bool, board: str):
    validate_board(board)
    table_row_counts = await get_row_counts([board])
    return await render_controller(
        template_stats_board,
        table_row_counts=table_row_counts,
        title='Stats',
        tab_title='Stats',
        logged_in=logged_in,
        is_admin=is_admin,
    )


@bp.route("/stats")
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def stats(logged_in: bool, is_admin: bool):
    return await render_controller(
        template_stats,
        board_objects=board_objects,
        title='Stats',
        tab_title='Stats',
        logged_in=logged_in,
        is_admin=is_admin,
    )
