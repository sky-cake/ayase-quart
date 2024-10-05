import asyncio
import os
from typing import NamedTuple

from quart import get_flashed_messages, request, url_for

from boards import get_shorts_objects, load_boards
from enums import IndexSearchType
from utils.timestamps import ts_2_formatted # temporary
from configs2 import app_conf, site_conf, search_conf, media_conf

class CONSTS(NamedTuple):
    """Jinja2 does not like type hinting, so they are not being written here for now."""

    TESTING = app_conf.get('testing', False)
    autoreload = app_conf.get('autoreload', True)
    validate_boards_db = app_conf.get('validate_boards_db', True)

    site_name = site_conf.get('name')

    if TESTING:
        site_port = app_conf.get('port', 9001)

    key_file = None # make_src_path('key.pem')
    cert_file = None # make_src_path('cert.pem')

    boards = load_boards()
    board_shortnames, board_objects = get_shorts_objects(boards)

    html_linked_target = '_self'  # or '_blank' # links to 4chan will always remain '_blank'

    theme = site_conf.get('theme', 'tomorrow')

    redis_url = '' # Optional. The redis URL for rate limiting. The default is usually 'redis://localhost:6379'

    root_dir = os.path.dirname(__file__)
    chdir_to_root = False
    static_dir = os.path.join(root_dir, "static")

    render_constants = dict(
        theme=theme,
        site_name=site_name,
        board_objects=board_objects,
        search=search_conf.get('enabled', False),
        image_uri=media_conf.get('image_uri'),
        thumb_uri=media_conf.get('thumb_uri'),
        html_linked_target=html_linked_target,
        index_search_provider=IndexSearchType(search_conf.get('provider')),
        index_search_host=search_conf.get('host'),
        url_for=url_for,
        request=request,
        get_flashed_messages=get_flashed_messages,
        format_ts=ts_2_formatted,
    )

def filter_boards_in_db():
    from moderation.api import get_db_tables

    db_tables = asyncio.run(get_db_tables(close_pool_after=True))
    valid_boards = {t for t in db_tables if len(t) < 5} & CONSTS.boards.keys()
    removals = [board for board in CONSTS.boards if board not in valid_boards]
    if removals:
        print(f'ATTENTION! Boards not found in database:\n\t[{", ".join(removals)}]\nThey will be ignored.')
        for b in removals:
            del CONSTS.boards[b]

    if not CONSTS.boards:
        raise ValueError(f'No boards to show! Configure one of {valid_boards}')

    # recompute these configs
    CONSTS.board_shortnames, CONSTS.board_objects = get_shorts_objects(CONSTS.boards)
    CONSTS.render_constants['board_objects'] = CONSTS.board_objects


if CONSTS.validate_boards_db:
    filter_boards_in_db()