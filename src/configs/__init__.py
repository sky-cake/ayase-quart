import os

from enums import DbType, PublicAccess
from utils import make_src_path
from vox import VoiceFlite, TranscriptMode
from .conf_loader import load_config_file
from .conf_common import massage_key

conf = load_config_file()
app_conf = conf.get('app', {})
massage_key(app_conf, 'login_endpoint', lambda x: f"/{x.strip('/')}")

site_conf = conf.get('site', {})
archive_conf = conf.get('archive', {'name': '4chan'})

db_conf = conf.get('db', {})
massage_key(db_conf, 'db_type', lambda x: DbType[x])

index_search_conf = conf.get('index_search', {})
vanilla_search_conf = conf.get('vanilla_search', {})

redis_conf = conf.get('redis', {})
media_conf = conf.get('media', {})

if not media_conf.get('media_root_path') and media_conf['serve_outside_static']:
    raise ValueError('`media_root_path` must be set so we know where to serve media from.', media_conf.get('media_root_path'))

def split_csv(csv_vals: str=None):
    if not csv_vals:
        return []
    return [x.strip() for x in csv_vals.strip(',').split(',')]

massage_key(media_conf, 'boards_with_image', split_csv)
massage_key(media_conf, 'boards_with_thumb', split_csv)

if media_conf['serve_outside_static']:
    if not os.path.isdir(media_conf.get('media_root_path')):
        raise ValueError(media_conf.get('media_root_path'))

    if not all(e for e in media_conf.get('valid_extensions')):
        raise ValueError(media_conf.get('valid_extensions'))
    media_conf['valid_extensions'] = tuple(media_conf.get('valid_extensions'))

    media_conf['endpoint'] = media_conf['endpoint'].strip().strip('/')
    if not media_conf['endpoint']:
        raise ValueError('The set media endpoint is falsey or root (/). Set it to something else.')


mod_conf = conf['moderation']
mod_conf['default_reported_post_public_access'] = PublicAccess.visible if mod_conf['default_reported_post_public_access'] == 'visible' else PublicAccess.hidden

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


archiveposting_conf = conf.get('archiveposting', {})
db_archiveposting_conf = archiveposting_conf
if archiveposting_conf['enabled'] and (' ' in archiveposting_conf['board_name'] or not archiveposting_conf['board_name'].replace('_', '').isalnum()):
    raise ValueError()


stats_conf = conf.get('stats', {'enabled': False})


vox_conf = conf.get('vox', {'enabled': False})
if vox_conf['enabled']:
    if vox_conf['reader_mode'] == 'dfs':
        vox_conf['reader_mode'] = TranscriptMode.dfs
    elif vox_conf['reader_mode'] == 'bfs':
        vox_conf['reader_mode'] = TranscriptMode.bfs
    elif vox_conf['reader_mode'] == 'op':
        vox_conf['reader_mode'] = TranscriptMode.op
    else:
        vox_conf['reader_mode'] = TranscriptMode.op_and_replies_to_op

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
if moderation_db := db_mod_conf.get('database'):
    db_mod_conf['database'] = moderation_db
if ssl_key := app_conf.get('ssl_key'):
    app_conf['ssl_key'] = make_src_path(ssl_key)
if ssl_cert := app_conf.get('ssl_cert'):
    app_conf['ssl_cert'] = make_src_path(ssl_cert)

class QuartConfig():
    TESTING = app_conf.get('testing', False)
    secret_key = app_conf.get('secret', 'DEFAULT_CHANGE_ME')
    if secret_key == 'DEFAULT_CHANGE_ME':
        from secrets import token_hex
        print('secret not set, generating random secret') # convert to logging.warning
        secret_key = token_hex(32)

    SECRET_KEY = secret_key

SITE_NAME = site_conf.get('name', 'Ayase Quart')
