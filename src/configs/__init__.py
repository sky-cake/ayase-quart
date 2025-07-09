import os

from enums import DbType
from utils import (
    make_src_path,
    strip_slashes as sslash,
)
from .conf_loader import load_config_file
from .conf_common import fuvii

sslash_both = lambda x: sslash(x, both=True)

conf = load_config_file()
app_conf = conf.get('app', {})
fuvii(app_conf, 'login_endpoint', lambda x: f"/{sslash_both(x)}")

site_conf = conf.get('site', {})

archive_conf = conf.get('archive', {})
fuvii(archive_conf, 'canonical_host', sslash)

db_conf = conf.get('db', {})
fuvii(db_conf, 'db_type', lambda x: DbType[x])

index_search_conf = conf.get('index_search', {})
vanilla_search_conf = conf.get('vanilla_search', {})

redis_conf = conf.get('redis', {})
media_conf = conf.get('media', {})

def split_csv(csv_vals: str=None):
    if not csv_vals:
        return []
    return [x.strip() for x in csv_vals.strip(',').split(',')]

fuvii(media_conf, 'boards_with_image', split_csv)
fuvii(media_conf, 'boards_with_thumb', split_csv)
fuvii(media_conf, 'image_uri', lambda x: sslash(x) if x else '')
fuvii(media_conf, 'thumb_uri', lambda x: sslash(x) if x else '')

if media_conf['serve_outside_static']:
    media_root = media_conf.get('media_root_path')
    if not media_root:
        raise ValueError(
            '`media_root_path` must be set so we know where to serve media from.',
            media_root,
        )
    if not os.path.isdir(media_root):
        raise ValueError(media_root)

    valid_exts = media_conf.get('valid_extensions')
    if not all(e for e in valid_exts):
        raise ValueError(valid_exts)
    fuvii(media_conf, 'valid_extensions', tuple)

    fuvii(media_conf, 'endpoint', sslash_both)
    if not media_conf['endpoint']:
        raise ValueError('The set media endpoint is falsey or root (/). Set it to something else.')


mod_conf = conf['moderation']

if hidden_images_path := mod_conf.get('hidden_images_path'):
    os.makedirs(hidden_images_path, exist_ok=True)
    if not os.path.isdir(hidden_images_path):
        raise ValueError(hidden_images_path)

db_mod_conf = mod_conf.get('sqlite', {}) # only supports sqlite atm
if mod_conf['enabled'] and db_mod_conf['database']:
    db_directory = os.path.dirname(db_mod_conf['database'])
    if not os.path.isdir(db_directory):
        raise ValueError(
            f"The moderation database directory does not exist: {db_directory}."
            f"You set [moderation][sqlite][database] = {db_mod_conf['database']}"
        )


def set_archiveposting_board(board: str|None):
    if not board or ' ' in board or not board.replace('_', '').isalnum():
        raise ValueError(f'Invalid archiveposting board: {board}')
    return board

archiveposting_conf = conf.get('archiveposting', {})
db_archiveposting_conf = archiveposting_conf
if archiveposting_conf['enabled']:
    fuvii(archiveposting_conf, 'board_name', set_archiveposting_board)


stats_conf = conf.get('stats', {'enabled': False})

def set_vox_transcription_mode(mode: str):
    from vox import TranscriptMode
    for tm in TranscriptMode:
        if tm.name == mode:
            return tm
    return TranscriptMode.op_and_replies_to_op

vox_conf = conf.get('vox', {'enabled': False})
if vox_conf['enabled']:
    from vox import VoiceFlite
    fuvii(vox_conf, 'reader_mode', set_vox_transcription_mode)

    if vox_conf['engine'] == 'flite':
        assert os.path.isfile(vox_conf['path_to_flite_binary'])
        assert os.path.isdir(vox_conf['path_to_flite_voices'])
        assert os.path.isdir(vox_conf['vox_root_path'])
        assert vox_conf['voice_narrator'] in VoiceFlite._member_names_


tag_conf = conf.get('tagging', {})
db_tag_conf = tag_conf # only supports sqlite atm
# # database might not be created yet, so we should not enforce this here
# if db_tag_conf['database'] and not os.path.isfile(db_tag_conf['database']):
#     raise ValueError(f'Can not find {db_tag_conf['database']}')


if sqlite_db := db_conf.get('sqlite', {}).get('database'):
    db_conf['database'] = make_src_path(sqlite_db)
# if moderation_db := db_mod_conf.get('database'):
#     db_mod_conf['database'] = moderation_db
fuvii(db_mod_conf, 'database') # ^ not sure what the logic of this one is

def make_src_path_if_exists(x):
    if not x:
        return x
    return make_src_path(x)
fuvii(app_conf, 'ssl_key', make_src_path_if_exists)
fuvii(app_conf, 'ssl_cert', make_src_path_if_exists)

class QuartConfig():
    TESTING = app_conf.get('testing', False)
    secret_key = app_conf.get('secret', 'DEFAULT_CHANGE_ME')
    if secret_key == 'DEFAULT_CHANGE_ME':
        from secrets import token_hex
        print('secret not set, generating random secret') # convert to logging.warning
        secret_key = token_hex(32)

    SECRET_KEY = secret_key

SITE_NAME = site_conf.get('name', 'Ayase Quart')
TESTING = app_conf.get('testing', False)
