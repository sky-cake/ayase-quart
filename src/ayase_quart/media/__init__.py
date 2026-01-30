from functools import cache
from urllib.parse import quote_plus

from ..configs import media_conf
from .filesystem import media_fs_partition
from ..search import BEST_SEARCH_ENDPOINT

THUMB_URI: str = media_conf.get('thumb_uri', '').rstrip('/')
IMAGE_URI: str = media_conf.get('image_uri', '').rstrip('/')
BOARDS_WITH_THUMB: tuple[str] = tuple(media_conf['boards_with_thumb'])
BOARDS_WITH_IMAGE: tuple[str] = tuple(media_conf['boards_with_image'])

media_partition = media_fs_partition

@cache
def ext_is_image(ext: str) -> bool:
    return ext in ('jpg', 'jpeg', 'png', 'bmp', 'webp') # gifs not included

@cache
def ext_is_video(ext: str) -> bool:
    return ext in ('webm', 'mp4')

@cache
def board_has_image(board: str) -> bool:
    return board in BOARDS_WITH_IMAGE and IMAGE_URI

@cache
def board_has_thumb(board: str) -> bool:
    return board in BOARDS_WITH_THUMB and THUMB_URI

@cache
def get_image_baseuri(board: str) -> str:
    return IMAGE_URI.format(board=board)

@cache
def get_thumb_baseuri(board: str) -> str:
    return THUMB_URI.format(board=board)

@cache
def get_hash_search_baseuri(board: str) -> str:
    if not BEST_SEARCH_ENDPOINT:
        return ''
    return f'{BEST_SEARCH_ENDPOINT}?boards={board}&media_hash='

def get_image_path(board: str, filename: str) -> str:
    if not(filename and board_has_image(board)):
        return ''
    return f'{get_image_baseuri(board)}/{media_partition(filename)}'

def get_thumb_path(board: str, filename: str) -> str:
    if not(filename and board_has_thumb(board)):
        return ''
    return f'{get_thumb_baseuri(board)}/{media_partition(filename)}'

def get_hash_search_link(board: str, media_hash: str) -> str:
    if not BEST_SEARCH_ENDPOINT:
        return ''
    return f'[<a href="{get_hash_search_baseuri(board)}{quote_plus(media_hash)}" target=_blank>View Same</a>]'
