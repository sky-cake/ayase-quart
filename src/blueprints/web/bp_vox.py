from quart import Blueprint, abort, send_file
import os
from quart_rate_limiter import rate_limit
from datetime import timedelta

from asagi_converter import generate_thread
from configs import app_conf, vox_conf
from moderation import fc
from threads import get_graph_from_thread
from utils import Perf
from utils.validation import validate_board, validate_threads
from vox import VoxFlite, make_transcript, get_vox_filepath, VoxKokoro


bp = Blueprint("bp_web_vox", __name__)


@bp.get("/<string:board_shortname>/thread/<int:thread_id>/vox")
@rate_limit(1, timedelta(minutes=5))
async def vox_thread(board_shortname: str, thread_id: int):
    validate_board(board_shortname)

    if not board_shortname in vox_conf['allowed_boards']:
        abort(403)

    p = Perf('thread_vox', enabled=app_conf.get('testing'))

    post_2_quotelinks, thread_dict = await generate_thread(board_shortname, thread_id)
    p.check('queries')

    thread_dict['posts'] = await fc.filter_reported_posts(thread_dict['posts'])
    p.check('filter_reported')

    validate_threads(thread_dict['posts'])
    p.check('validate')

    ext = 'mp3'
    if vox_conf['engine'] == 'flite':
        ext = 'wav'

    vox_filepath = get_vox_filepath(vox_conf['vox_root_path'], board_shortname, thread_id, ext)
    if not os.path.isfile(vox_filepath):

        g = get_graph_from_thread(post_2_quotelinks, thread_dict['posts'])
        p.check('graph')

        transcript = make_transcript(g, mode=vox_conf['reader_mode'])
        p.check('transcript')

        if vox_conf['engine'] == 'flite':
            VoxFlite(vox_conf).write(transcript, spoken_speed=1.0, wav_output_filepath=vox_filepath)
        else:
            VoxKokoro().write(transcript, vox_filepath)

        p.check('vox')

        if not vox_filepath:
            abort(404)

        if not vox_filepath.split('.')[-1].lower().endswith(ext):
            abort(404)

        if not vox_filepath.startswith(vox_conf['vox_root_path']):
            abort(404)

        if not os.path.isfile(vox_filepath):
            abort(404)

    print(p)
    return await send_file(vox_filepath, cache_timeout=None)
