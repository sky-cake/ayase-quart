from quart import Blueprint

from enums import SearchType
from search import search_handler

bp = Blueprint("bp_web_vanilla_search", __name__)


@bp.route("/vanilla_search", methods=['GET', 'POST'])
async def v_vanilla_search():
    return await search_handler(SearchType.sql)
