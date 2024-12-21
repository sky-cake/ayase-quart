from werkzeug.exceptions import NotFound

import boards


def validate_board(board: str) -> None:
    if not board in boards.boards:
        raise NotFound(board, boards.board_shortnames)


def validate_threads(threads: list[dict]):
    if len(threads) < 1:
        raise NotFound(threads)


def clamp_positive_int(value: int|float|str, lower: int=0, upper: int=None) -> int:
    """Clamps a value within the range:

    `lower <= abs(int(value)) <= upper`
    """
    value = max(abs(int(value)), lower)
    if upper is not None:
        value = min(value, upper)
    return value
