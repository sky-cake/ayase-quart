from functools import cache
import tomllib

from utils import make_src_path

CONF_FILE = 'config.toml'
TEST_CONF_FILE = 'config-test.toml' # not used yet

# figure out how to integrate pytest with testing later.
def load_config_file(testing: bool=False) -> dict:
    conf_file = TEST_CONF_FILE if testing else CONF_FILE
    return _load_config_toml(conf_file)

@cache
def _load_config_toml(filename: str) -> dict:
    with open(make_src_path(filename), 'rb') as f:
        return tomllib.load(f)
