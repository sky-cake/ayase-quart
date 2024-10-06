import tomllib
from utils import make_src_path

def load_config_toml():
    if not hasattr(load_config_toml, 'conf'):
        with open('config.toml', 'rb') as f:
           load_config_toml.conf = tomllib.load(f)
    return load_config_toml.conf

conf = load_config_toml()
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

class QuartConfig():
    TESTING = app_conf.get('testing', False)
    if secret_key := app_conf.get('secret', 'DEFAULT_CHANGE_ME') == 'DEFAULT_CHANGE_ME':
        from secrets import token_hex
        print('secret not set, generating random secret') # convert to logging.warning
        secret_key = token_hex(32)
    SECRET_KEY = secret_key