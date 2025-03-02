from quart import Blueprint

from enums import SearchType
from search import search_handler
from moderation.auth import web_usr_logged_in

bp = Blueprint("bp_web_vanilla_search", __name__)


@bp.route("/vanilla_search", methods=['GET', 'POST'])
@web_usr_logged_in
async def v_vanilla_search(logged_in: bool):
    return await search_handler(SearchType.sql, logged_in=logged_in)
