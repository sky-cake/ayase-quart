import tomllib
from utils import make_src_path

def _load_config_toml():
    if not hasattr(_load_config_toml, 'conf'):
        with open('config.toml', 'rb') as f:
           _load_config_toml.conf = tomllib.load(f)
    return _load_config_toml.conf

conf = _load_config_toml()
app_conf = conf.get('app', {})
site_conf = conf.get('site', {})
db_conf = conf.get('db', {})
search_conf = conf.get('search', {})
redis_conf = conf.get('redis', {})
media_conf = conf.get('media', {})
moderation_conf = conf.get('moderation', {})

if sqlite_db := db_conf.get('sqlite', {}).get('database'):
    db_conf['sqlite']['database'] = make_src_path(sqlite_db)
if moderation_db := moderation_conf.get('sqlite', {}).get('database'):
    moderation_conf['sqlite']['database'] = make_src_path(moderation_db)
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