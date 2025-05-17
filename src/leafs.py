import os

from werkzeug.security import safe_join

from asagi_converter import generate_post
from configs import media_conf, mod_conf
from posts.template_optimizer import wrap_post_t
from posts.template_optimizer import render_wrapped_post_t


async def generate_post_html(board_shortname: str, num: int, db_X=None) -> str:
    """Removes [Report]"""
    post_2_quotelinks, post = await generate_post(board_shortname, num, db_X=db_X)
    if not post:
        return 'Error fetching post.'
    post_t = wrap_post_t(post | dict(quotelinks={})) | dict(t_report='')
    return render_wrapped_post_t(post_t)


def get_path_for_media(root_path: str, board_shortname: str, media_name: str, is_thumb: bool) -> str:
    """media_name is post.media_orig or post.preview_orig"""
    path = None

    if not (root_path and board_shortname):
        raise ValueError(root_path, board_shortname, media_name)

    if media_name and len(media_name) >= 6:
        qualifier = 'thumb' if is_thumb else 'image'
        path = safe_join(root_path, board_shortname, qualifier, media_name[0:4], media_name[4:6], media_name)

    return path


def post_file_hide(board_shortname: str, media_name: str, is_thumb: bool) -> bool:
    """Assumes media src is in `media_root_path`"""

    if not media_name:
        return False

    src = get_path_for_media(media_conf['media_root_path'], board_shortname, media_name, is_thumb)
    if src and os.path.isfile(src):
        dst = get_path_for_media(mod_conf['hidden_images_path'], board_shortname, media_name, is_thumb)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.rename(src, dst)
        return True
    return False


def post_files_hide(post: dict) -> tuple[bool]:
    return (
        post_file_hide(post['board_shortname'], post.get('media_orig'), False),
        post_file_hide(post['board_shortname'], post.get('preview_orig'), True)
    )


def post_files_delete(post: dict) -> tuple[bool]:
    return (
        post_file_delete(post['board_shortname'], post.get('media_orig'), False),
        post_file_delete(post['board_shortname'], post.get('preview_orig'), True)
    )


def post_files_show(post: dict) -> tuple[bool]:
    return (
        post_file_show(post['board_shortname'], post.get('media_orig'), False),
        post_file_show(post['board_shortname'], post.get('preview_orig'), True)
    )


def post_file_show(board_shortname: str, media_name: str, is_thumb: bool) -> bool:
    """Assumes media src is in `hidden_images_path`"""

    if not media_name:
        return False

    src = get_path_for_media(mod_conf['hidden_images_path'], board_shortname, media_name, is_thumb)
    if src and os.path.isfile(src):
        dst = get_path_for_media(media_conf['media_root_path'], board_shortname, media_name, is_thumb)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.rename(src, dst)
        return True
    return False


def post_file_delete(board_shortname: str, media_name: str, is_thumb: bool) -> bool:
    if not media_name:
        return False

    # already hidden?
    src = get_path_for_media(mod_conf['hidden_images_path'], board_shortname, media_name, is_thumb)
    if src and os.path.isfile(src):
        os.remove(src)
        return True

    # still available?
    src = get_path_for_media(media_conf['media_root_path'], board_shortname, media_name, is_thumb)
    if src and os.path.isfile(src):
        os.remove(src)
        return True

    return False
