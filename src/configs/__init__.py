import os

from enums import DbType
from utils import make_src_path, split_csv
from utils import strip_slashes as sslash

from .conf_common import fuvii
from .conf_loader import load_config_file

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


stats_conf = conf.get('stats', {'enabled': False})


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
