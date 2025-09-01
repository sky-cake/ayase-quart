from datetime import timedelta

from quart import Blueprint, request, url_for
from quart_rate_limiter import rate_limit

from moderation.auth import (
    load_web_usr_data,
    web_usr_is_admin,
    web_usr_logged_in
)
from blueprints.web.bp_search import search_handler, SearchHandlerFTS

bp = Blueprint("bp_web_index_search", __name__)

@bp.get('/fts')
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
@rate_limit(5, timedelta(minutes=1))
async def v_index_search_get(is_admin: bool, logged_in: bool):
    endpoint_path = url_for('bp_web_index_search.v_index_search_get')
    return await search_handler(SearchHandlerFTS(), request.args.to_dict(flat=True), endpoint_path, logged_in=logged_in, is_admin=is_admin)
