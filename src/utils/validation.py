from quart import abort

import boards


def validate_board(board: str) -> None:
    if not board in boards.boards:
        abort(404)


def validate_threads(threads: list[dict]):
    if len(threads) < 1:
        abort(404)


def clamp_positive_int(value: int|float|str, lower: int=0, upper: int=None) -> int:
    """Clamps a value within the range:

    `lower <= abs(int(value)) <= upper`
    """
    value = max(abs(int(value)), lower)
    if upper is not None:
        value = min(value, upper)
    return value
