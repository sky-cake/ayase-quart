from quart import Blueprint
from render import render_controller
from templates import template_about

bp = Blueprint("bp_web_about", __name__)


@bp.route("/about", methods=['GET'])
async def v_about():
    return await render_controller(
        template_about,
        title='About',
        tab_title='About',
        is_admin=True,
    )