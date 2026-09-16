from functools import cache, lru_cache

from .configs import archive_conf

@cache
def get_board_upstream(board: str) -> str:
    return f'{archive_conf.canonical_host}/{board}'

@cache
def get_catalog_upstream(board: str) -> str:
    return f'{get_board_upstream(board)}{archive_conf.catalog_path}'

@lru_cache(maxsize=4096)
def get_thread_upstream(board: str, thread_num: int) -> str:
    return f'{get_board_upstream(board)}{archive_conf.thread_path.format(thread=thread_num)}'

def get_post_upstream(board: str, thread_num: int, num: int) -> str:
    return f'{get_thread_upstream(board, thread_num)}{archive_conf.post_path.format(num=num)}'
