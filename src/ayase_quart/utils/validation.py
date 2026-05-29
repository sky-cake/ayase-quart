from quart import abort
from functools import wraps
from urllib.parse import unquote

from .. import boards


def validate_board(board: str) -> None:
    if not board or board not in boards.boards:
        abort(404)


def validate_boards(board_names: str) -> None:
    for board_name in board_names:
        validate_board(board_name)


def validate_board_query_parameter(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        board = kwargs.get('board')

        if not isinstance(board, str):
            abort(400)

        board = unquote(board, encoding='utf-8', errors='strict')
        validate_board(board)
        kwargs['board'] = board

        return await func(*args, **kwargs)

    return wrapper
