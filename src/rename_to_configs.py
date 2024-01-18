from datetime import timedelta
from typing import NamedTuple

import os


def make_path(*file_path):
    """Make a file path as though this file's directory is a root directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), *file_path))


class CONSTS(NamedTuple):
    TESTING = True # public url, hypercorn server debugging mode, etc.

    REVERSE_PROXY = False
    
    db_host = '192.168.0.123'
    db_port = 3306
    db_database = 'hayden'
    db_user = 'username'
    db_password = 'password'
    db_min_connections = 3
    db_max_connections = 10

    SQLALCHEMY_ECHO = False

    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB upload capacity

    with open(make_path("secret.txt"), encoding="utf-8") as f:
        SECRET_KEY = f.read().strip()


    site_name = "Ayase Quart"
    site_url = "https://example.com"

    if TESTING:
        site_host = "127.0.0.1"
        site_port = 9001
        site_url = f"http://{site_host}:{site_port}"


    root_dir = os.path.dirname(__file__)
    chdir_to_root = True

    static_dir = os.path.join(root_dir, "static")
    
    hash_format: str = 'md5' # md5, sha256 # (only md5 has been tested)

    site_name: str = 'Ayase Quart'

    board_objects = [
        {'shortname': 'ck', 'name': 'Food & Cooking'},
        {'shortname': 'trv', 'name': 'Travel'},
        {'shortname': 'g', 'name': 'Technology'},
        {'shortname': 't', 'name': 'Torrents'},
        {'shortname': 'mu', 'name': 'Music'},
    ]

    board_shortname_to_name = {o['shortname']: o['name'] for o in board_objects}

    image_location = {
        'image': "/static/hayden_asagi/{board_shortname}/image", # must contain {board_shortname}
        'thumb': "/static/hayden_asagi/{board_shortname}/thumb", # must contain {board_shortname}
    }

    theme = 'tomorrow' # 'tomorrow' 'yotsuba' 'yotsuba_b' 'futaba' 'burichan' 'photon'

    search = True
    search_result_limit = 100

    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB upload capacity

    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##

    board_shortnames = [board_object['shortname'] for board_object in board_objects]

    render_constants = dict(
        theme = theme,
        site_name = site_name,
        sha256_dirs = hash_format=='sha256',
        board_objects = board_objects,
        search=search,
    )
