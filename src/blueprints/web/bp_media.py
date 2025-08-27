import os
import re

from quart import Blueprint, abort
from werkzeug.security import safe_join

from configs import media_conf
from utils.web_helpers import send_file_no_headers

bp = Blueprint("bp_app_media", __name__)


def should_be_served(file_path, typ: str) -> bool:
    re_board = '[a-zA-Z0-9]{1,5}'
    match = re.search(f'/({re_board})/{typ}/', file_path)
    if match:
        return False
    return True


if media_conf.get('endpoint') and media_conf['serve_outside_static']:
    @bp.route(f'/{media_conf['endpoint']}/<path:file_path>')
    async def serve(file_path: str):
        if media_conf['boards_with_image'] and not should_be_served(file_path, 'image'):
            abort(404)

        if media_conf['boards_with_thumb'] and not should_be_served(file_path, 'thumb'):
            abort(404)

        file_path = safe_join(media_conf['media_root_path'], file_path)

        if not file_path:
            abort(404)

        if not file_path.split('.')[-1].lower().endswith(media_conf['valid_extensions']):
            abort(404)

        if not file_path.startswith(media_conf['media_root_path']):
            abort(404)

        if not os.path.isfile(file_path):
            abort(404)

        return await send_file_no_headers(file_path)
