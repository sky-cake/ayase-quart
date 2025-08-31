from quart import Blueprint

from configs import site_conf
from moderation.auth import (
    load_web_usr_data,
    web_usr_is_admin,
    web_usr_logged_in
)
from render import render_controller
from templates import template_about, template_soy

bp = Blueprint("bp_web_about", __name__)


@bp.get("/about")
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def about(is_admin: bool, logged_in: bool):
    return await render_controller(
        template_about,
        tab_title='About',
        logged_in=logged_in,
        is_admin=is_admin,
        site_email=site_conf['site_email'],
    )


@bp.get("/soy")
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def soy(is_admin: bool, logged_in: bool):
    return await render_controller(
        template_soy,
        title='... unsafe search... the boy is curious...',
        logged_in=logged_in,
        is_admin=is_admin,
    )
