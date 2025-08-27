import asyncio
import os
from functools import cache
from tomllib import load

from configs import app_conf, archiveposting_conf, db_conf, media_conf
from db import get_db_tables
from utils import make_src_path

BOARDS_FILE = make_src_path('boards.toml')
DEFAULT_BOARDS_FILE = make_src_path('boards.tpl.toml')

def _load_boards_toml():
    if not hasattr(_load_boards_toml, 'boards'):
        board_file = None
        if os.path.exists(BOARDS_FILE):
            board_file = BOARDS_FILE
        elif os.path.exists(DEFAULT_BOARDS_FILE):
            board_file = DEFAULT_BOARDS_FILE
        if board_file is None:
            return {}
        with open(board_file, 'rb') as f:
            toml_d = load(f)
            _load_boards_toml.boards = toml_d.get('boards', {})
    return _load_boards_toml.boards


def get_shorts_objects(boards: dict):
    '''return (board_shorts, board_objects)'''
    board_shorts = sorted([board for board in boards])
    board_objects = [{'shortname': short, 'name': long} for short, long in boards.items()]
    board_objects.sort(key=lambda x: x['shortname'])
    return board_shorts, board_objects


def _get_board_views():
    boards = _load_boards_toml()
    if app_conf.get('validate_boards_db', True):
        db_tables = asyncio.run(get_db_tables(db_conf, db_conf['db_type'], close_pool_after=True))
        valid_boards = {t for t in db_tables if len(t) < 5} & boards.keys()
        if removals := [board for board in boards if board not in valid_boards]:
            # print(f'Boards not found in database:\n\t[{", ".join(removals)}]\nWill be ignored.')
            for b in removals:
                del boards[b]
    if not boards:
        raise ValueError(f'No boards to show! Configure one of {valid_boards}')
    board_shorts, board_objects = get_shorts_objects(boards)
    print('Serving: ', board_shorts)
    return boards, board_shorts, board_objects


boards, board_shortnames, board_objects = _get_board_views()
if archiveposting_conf['enabled'] and archiveposting_conf['board_name'] in board_shortnames:
    raise ValueError()

for b in media_conf['boards_with_thumb']:
    if b not in board_shortnames:
        raise ValueError(f'Unknown board specified for serving thumb media with `boards_with_thumb`: {b}')

for b in media_conf['boards_with_image']:
    if b not in board_shortnames:
        raise ValueError(f'Unknown board specified for serving full media with `boards_with_image`: {b}')

@cache
def get_title(board: str):
    title = f"/{board}/ - {boards[board]}"
    return title
