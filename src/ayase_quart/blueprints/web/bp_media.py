import os

from quart import Blueprint, abort, Response
from werkzeug.security import safe_join

from ...configs import media_conf
from ...utils.web_helpers import send_file_no_headers

bp = Blueprint("bp_app_media", __name__)


if media_conf.get('endpoint') and media_conf['serve_outside_static']:
    media_root = media_conf['media_root_path']

    valid_exts = set(media_conf['valid_extensions'])
    boards_with_image = set(media_conf['boards_with_image'])
    boards_with_thumb = set(media_conf['boards_with_thumb'])

    use_nginx_sendfile = media_conf.get('use_nginx_sendfile', False)
    nginx_x_accel_redirect_path = media_conf.get('nginx_x_accel_redirect', False)


    @bp.route(f'/{media_conf["endpoint"]}/<path:suffix_path>')
    async def serve(suffix_path: str):
        # file_path = 'g/thumb/1763/69/1763698364803744s.jpg'
        # file_path = 'g/image/1763/67/1763679461297674.jpg'

        board = suffix_path.split('/', maxsplit=1)[0]
        if not board:
            abort(404)

        if suffix_path.startswith(f'{board}/image/') and board not in boards_with_image:
            abort(404)
        elif suffix_path.startswith(f'{board}/thumb/') and board not in boards_with_thumb:
            abort(404)

        full_path = safe_join(media_root, suffix_path)
        if not full_path:
            abort(404)

        # faith in safe_join
        # if not full_path.startswith(media_root):
        #     abort(404)

        if full_path.rsplit('.', 1)[-1].lower() not in valid_exts:
            abort(404)

        if not os.path.isfile(full_path):
            abort(404)

        if use_nginx_sendfile:
            return Response(
                status=200,
                headers={'X-Accel-Redirect': safe_join(nginx_x_accel_redirect_path, full_path)},
            )

        return await send_file_no_headers(full_path)
