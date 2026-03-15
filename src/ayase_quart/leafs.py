import os

from .asagi_converter import generate_post
from .posts.template_optimizer import render_wrapped_post_t, wrap_post_t
from .media.filesystem import get_fs_path, MediaType


async def generate_post_html(board: str, num: int) -> str:
    """Removes [Report]"""
    post_2_quotelinks, post = await generate_post(board, num)
    if not post:
        return 'Error fetching post.'
    post_t = wrap_post_t(post | dict(quotelinks={})) | dict(t_report='')
    return render_wrapped_post_t(post_t)


def post_files_hide(post: dict) -> tuple[bool]:
    return (
        _post_files_hide(post, MediaType.full_media),
        _post_files_hide(post, MediaType.thumbnail),
    )


def post_files_delete(post: dict) -> tuple[bool]:
    return (
        _post_files_delete(post, MediaType.full_media),
        _post_files_delete(post, MediaType.thumbnail),
    )


def post_files_show(post: dict) -> tuple[bool]:
    return (
        _post_files_show(post, MediaType.full_media),
        _post_files_show(post, MediaType.thumbnail),
    )


def _post_files_hide(post: dict, media_type: MediaType) -> bool:
    """accessible path -> hidden path"""
    src = get_fs_path(post, media_type)
    if src and os.path.isfile(src):
        dst = get_fs_path(post, media_type, hidden=True)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.replace(src, dst)
        return True
    return False


def _post_files_show(post: dict, media_type: MediaType) -> bool:
    """hidden path -> accessible path"""
    src = get_fs_path(post, media_type, hidden=True)
    if src and os.path.isfile(src):
        dst = get_fs_path(post, media_type)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.replace(src, dst)
        return True
    return False


def _post_files_delete(post: dict, media_type: MediaType) -> bool:
    # already hidden?
    src = get_fs_path(post, media_type, hidden=True)
    if src and os.path.isfile(src):
        os.remove(src)
        return True

    # still accessible?
    src = get_fs_path(post, media_type)
    if src and os.path.isfile(src):
        os.remove(src)
        return True

    return False
