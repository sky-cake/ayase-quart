import os
from tomllib import load

from utils import make_src_path

BOARDS_FILE = make_src_path('boards.toml')
DEFAULT_BOARDS_FILE = make_src_path('boards.tpl.toml')

def load_boards():
    if not hasattr(load_boards, 'boards'):
        board_file = None
        if os.path.exists(BOARDS_FILE):
            board_file = BOARDS_FILE
        elif os.path.exists(DEFAULT_BOARDS_FILE):
            board_file = DEFAULT_BOARDS_FILE
        if board_file is None:
            return {}
        with open(board_file, 'rb') as f:
            toml_d = load(f)
            load_boards.boards = toml_d.get('boards', {})
    return load_boards.boards

def get_shorts_objects(boards: dict):
    '''return (board_shorts, board_objects)'''
    board_shorts = [board for board in boards]
    board_objects = [{'shortname': short, 'name': long} for short, long in boards.items()]
    board_objects.sort(key=lambda x: x['shortname'])
    return board_shorts, board_objects