from enum import StrEnum
from werkzeug.security import safe_join

from ..enums import MediaFP
from ..configs import media_conf, mod_conf


ROOT_PATH = media_conf['media_root_path']
ROOT_HIDDEN_PATH = mod_conf['hidden_images_path']


if media_conf['media_fp'] == MediaFP.sutra:


    class MediaType(StrEnum):
        full_media = 'img'
        thumbnail = 'thb'


    sutra_translate_table = str.maketrans({'+': '-', '/': '_'})
    def get_fs_path(post: dict, media_type: MediaType, hidden: bool=False) -> str | None:
        if media_type == MediaType.full_media:
            ext = post.get('ext')
        elif media_type == MediaType.thumbnail:
            ext = '.jpg'
        else:
            raise ValueError(media_type)
        
        media_hash = post.get('media_hash')
        if not media_hash or not ext:
            return

        filename = f'{media_hash.translate(sutra_translate_table)}{ext}'
        return safe_join(
            ROOT_HIDDEN_PATH if hidden else ROOT_PATH,
            media_type.value,
            filename[0:2],
            filename[2:4],
            filename[4:6],
            filename,
        )


    def get_media_splits(post: dict, media_type: MediaType) -> str:
        """No padding slashes"""
        if media_type == MediaType.full_media:
            ext = post.get('ext')
        elif media_type == MediaType.thumbnail:
            ext = '.jpg'
        else:
            raise ValueError(media_type)

        media_hash = post.get('media_hash')
        if not media_hash or not ext:
            return

        filename = f'{media_hash.translate(sutra_translate_table)}{ext}'
        if not filename:
            return ''

        return f'{filename[0:2]}/{filename[2:4]}/{filename[4:6]}/{filename}'


elif media_conf['media_fp'] == MediaFP.asagi:


    class MediaType(StrEnum):
        full_media = 'image'
        thumbnail = 'thumb'


    def get_fs_path(post: dict, media_type: MediaType, hidden: bool=False) -> str | None:
        if media_type == MediaType.full_media:
            filename = post.get('media_orig')
        elif media_type == MediaType.thumbnail:
            filename = post.get('preview_orig')
        else:
            raise ValueError(media_type)
        
        if not filename:
            return

        return safe_join(
            ROOT_HIDDEN_PATH if hidden else ROOT_PATH,
            post['board_shortname'],
            media_type.value,
            filename[0:4],
            filename[4:6],
            filename,
        )


    def get_media_splits(post: dict, media_type: MediaType) -> str:
        """No padding slashes"""
        if media_type == MediaType.full_media:
            filename = post.get('media_orig')
        elif media_type == MediaType.thumbnail:
            filename = post.get('media_preview')
        else:
            raise ValueError(media_type)
        
        if not filename:
            return ''

        return f'{filename[0:4]}/{filename[4:6]}/{filename}'
            


else:
    raise ValueError(media_conf['media_fp'])
