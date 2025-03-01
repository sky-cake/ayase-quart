import os
import tomllib

from enums import DbType, PublicAccess
from utils import make_src_path


def _load_config_toml():
    if not hasattr(_load_config_toml, 'conf'):
        with open(make_src_path('config.toml'), 'rb') as f:
           _load_config_toml.conf = tomllib.load(f)
    return _load_config_toml.conf

conf = _load_config_toml()
app_conf = conf.get('app', {})
site_conf = conf.get('site', {})
archive_conf = conf.get('archive', {'name': '4chan'})

db_conf = conf.get('db', {})
db_conf['db_type'] = DbType[db_conf['db_type']]

index_search_conf = conf.get('index_search', {})
vanilla_search_conf = conf.get('vanilla_search', {})

# not supported yet... searching for "a " will match "<a href..." and break links
# other tags break too, of course
index_search_conf['highlight'] = False
vanilla_search_conf['highlight'] = False

redis_conf = conf.get('redis', {})
media_conf = conf.get('media', {})

if not media_conf.get('media_root_path') and media_conf['serve_outside_static']:
    raise ValueError('`media_root_path` must be set so we know where to serve media from.', media_conf.get('media_root_path'))

if media_conf['serve_outside_static']:
    if not os.path.isdir(media_conf.get('media_root_path')):
        raise ValueError(media_conf.get('media_root_path'))

    if not all(e for e in media_conf.get('valid_extensions')):
        raise ValueError(media_conf.get('valid_extensions'))
    media_conf['valid_extensions'] = tuple(media_conf.get('valid_extensions'))

    media_conf['endpoint'] = media_conf['endpoint'].strip().strip('/')
    if not media_conf['endpoint']:
        raise ValueError('The set media endpoint is falsey or root (/). Set it to something else.')


mod_conf = conf.get('moderation', {})
mod_conf['default_reported_post_public_access'] = PublicAccess.visible if mod_conf['default_reported_post_public_access'] == 'visible' else PublicAccess.hidden

if hidden_images_path := mod_conf.get('hidden_images_path'):
    os.makedirs(hidden_images_path, exist_ok=True)
    if not os.path.isdir(hidden_images_path):
        raise ValueError(hidden_images_path)

db_mod_conf = mod_conf.get('sqlite', {}) # only supports sqlite atm

if sqlite_db := db_conf.get('sqlite', {}).get('database'):
    db_conf['database'] = make_src_path(sqlite_db)
if moderation_db := db_mod_conf.get('database'):
    db_mod_conf['database'] = make_src_path(moderation_db)
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