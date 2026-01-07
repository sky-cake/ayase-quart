from functools import cache, lru_cache

from configs import archive_conf

CANONICAL_HOST: str = archive_conf['canonical_host']
CANONICAL_NAME: str = archive_conf['canonical_name']
THREAD_SRC_PATH: str = archive_conf.get('thread_path', '/thread/{thread}')
POST_SRC_PATH: str = archive_conf.get('post_path', '#p{num}')
CATALOG_SRC_PATH: str = archive_conf.get('catalog_path', '/catalog')

@cache
def get_board_upstream(board: str) -> str:
    return f'{CANONICAL_HOST}/{board}'

@cache
def get_catalog_upstream(board: str) -> str:
    return f'{get_board_upstream(board)}{CATALOG_SRC_PATH}'

@lru_cache(maxsize=4096)
def get_thread_upstream(board: str, thread_num: int) -> str:
    return f'{get_board_upstream(board)}{THREAD_SRC_PATH.format(thread=thread_num)}'

def get_post_upstream(board: str, thread_num: int, num) -> str:
    return f'{get_thread_upstream(board, thread_num)}{POST_SRC_PATH.format(num=num)}'
