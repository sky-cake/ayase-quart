from quart import Blueprint, jsonify
from tagging.db import get_tags


bp = Blueprint("bp_web_tagging", __name__)


@bp.get("/tags")
async def tags():
    return jsonify(await get_tags())
