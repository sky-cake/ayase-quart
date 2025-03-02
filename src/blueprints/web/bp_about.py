from quart import Blueprint
from render import render_controller
from templates import template_about
from moderation.auth import web_usr_logged_in

bp = Blueprint("bp_web_about", __name__)


@bp.get("/about")
@web_usr_logged_in
async def v_about(logged_in: bool):
    return await render_controller(
        template_about,
        title='About',
        tab_title='About',
        logged_in=logged_in,
    )