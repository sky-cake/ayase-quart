from quart import Blueprint

from enums import SearchType
from search import search_handler


bp = Blueprint("bp_web_index_search", __name__)


@bp.route("/index_search", methods=['GET', 'POST'])
async def v_index_search():
    return await search_handler(SearchType.idx)
