import os

from quart import Blueprint, abort, send_file
from werkzeug.security import safe_join

from configs import media_conf

bp = Blueprint("bp_app_media", __name__)

if media_conf.get('endpoint') and media_conf['serve_outside_static']:
    @bp.route(f'/{media_conf['endpoint']}/<path:file_path>')
    async def serve(file_path: str):
        file_path = safe_join(media_conf['media_root_path'], file_path)

        if not file_path:
            abort(404)

        if not file_path.split('.')[-1].lower().endswith(media_conf['valid_extensions']):
            abort(404)

        if not file_path.startswith(media_conf['media_root_path']):
            abort(404)

        if not os.path.isfile(file_path):
            abort(404)

        return await send_file(file_path, cache_timeout=None)
