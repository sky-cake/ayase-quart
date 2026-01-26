import os

from quart import Blueprint, abort
from werkzeug.security import safe_join

from ...configs import media_conf
from ...utils.web_helpers import send_file_no_headers

bp = Blueprint("bp_app_media", __name__)


if media_conf.get('endpoint') and media_conf['serve_outside_static']:
    media_root = media_conf['media_root_path']
    valid_ext = media_conf['valid_extensions']
    boards_with_image = media_conf['boards_with_image']
    boards_with_thumb = media_conf['boards_with_thumb']

    img = '/image/'
    thb = '/thumb/'

    @bp.route(f'/{media_conf["endpoint"]}/<path:file_path>')
    async def serve(file_path: str):
        # file_path = 'g/thumb/1763/69/1763698364803744s.jpg'
        # file_path = 'g/image/1763/67/1763679461297674.jpg'
        if boards_with_image and img not in file_path:
            abort(404)

        if boards_with_thumb and thb not in file_path:
            abort(404)

        full_path = safe_join(media_root, file_path)
        if not full_path:
            abort(404)

        if not full_path.startswith(media_root):
            abort(404)

        if not full_path.rsplit('.', 1)[-1].lower().endswith(valid_ext):
            abort(404)

        if not os.path.isfile(full_path):
            abort(404)

        return await send_file_no_headers(full_path)
