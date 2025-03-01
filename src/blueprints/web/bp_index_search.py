from logging import getLogger

from quart import Blueprint

from boards import board_shortnames
from configs import SITE_NAME
from enums import SearchType
from render import render_controller
from search import search_handler
from search.providers import get_index_search_provider
from templates import template_search_info

search_log = getLogger('search')

bp = Blueprint("bp_web_index_search", __name__)


@bp.route("/index_search_config", methods=['GET', 'POST'])
async def index_search_config():
    return await render_controller(
        template_search_info,
        title=SITE_NAME,
        tab_title=SITE_NAME,
        board_list=' '.join(board_shortnames),
    )


@bp.route("/index_stats", methods=['GET'])
async def index_search_stats():
    search_p = get_index_search_provider()
    return await search_p.post_stats()


@bp.route("/index_search", methods=['GET', 'POST'])
async def v_index_search():
    return await search_handler(SearchType.idx)
