from asagi_converter import (
    convert_thread,
    generate_index,
    generate_catalog,
)
from quart import Blueprint
from utils import validate_board_shortname


blueprint_api = Blueprint("blueprint_api", __name__, template_folder="templates")


@blueprint_api.get("/<string:board_shortname>/catalog.json")
async def catalog(board_shortname: str):
    validate_board_shortname(board_shortname)

    return await generate_catalog(board_shortname, 1)


@blueprint_api.get("/<string:board_shortname>/thread/<int:thread_id>.json")
async def thread(board_shortname: str, thread_id: int):

    validate_board_shortname(board_shortname)

    res = await convert_thread(board_shortname, thread_id)

    if res and len(res) > 0 and res[0].get("posts", False):
        return res


@blueprint_api.get("/<string:board_shortname>/<int:page_num>.json")
async def board_index(board_shortname: str, page_num: int):
    
    validate_board_shortname(board_shortname)

    res = await generate_index(board_shortname, page_num, html=False)
    if res and res.get("threads"):
        return res
