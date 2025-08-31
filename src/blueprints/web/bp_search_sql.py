from datetime import timedelta

from quart import Blueprint
from quart_rate_limiter import rate_limit

from enums import SearchType
from moderation.auth import (
    load_web_usr_data,
    web_usr_is_admin,
    web_usr_logged_in
)
from blueprints.web.bp_search import search_handler

bp = Blueprint("bp_web_vanilla_search", __name__)


@bp.get("/sql")
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
@rate_limit(3, timedelta(minutes=1))
async def v_vanilla_search_get(is_admin: bool, logged_in: bool):
    return await search_handler(SearchType.sql, logged_in=logged_in, is_admin=is_admin)


# @bp.post("/sql")
# @load_web_usr_data
# @web_usr_logged_in
# @web_usr_is_admin
# @rate_limit(1, timedelta(minutes=5))
# async def v_vanilla_search_post(is_admin: bool, logged_in: bool):
#     return await search_handler(SearchType.sql, logged_in=logged_in, is_admin=is_admin)
