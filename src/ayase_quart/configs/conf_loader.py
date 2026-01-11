import tomllib
import json
from functools import cache

CONF_FILE = 'config.toml'
TEST_CONF_FILE = 'config-test.toml' # not used yet
ASSET_HASHES_FILE = 'asset_hashes.json'

# figure out how to integrate pytest with testing later.
def load_config_file(testing: bool=False) -> dict:
    conf_file = TEST_CONF_FILE if testing else CONF_FILE
    return _load_config_toml(conf_file)

@cache
def _load_config_toml(filename: str) -> dict:
    with open(filename, 'rb') as f:
        return tomllib.load(f)

@cache
def _load_json_file(filename: str) -> dict:
    with open(filename, 'rb') as f:
        return json.load(f)

def load_asset_hashes() -> dict:
    if not hasattr(load_asset_hashes, 'hashes'):
        try:
            hashes = _load_json_file(ASSET_HASHES_FILE)
        except:
            hashes = {}
        load_asset_hashes.hashes = hashes
    return load_asset_hashes.hashes
