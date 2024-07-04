import os
from typing import NamedTuple


def make_path(*file_path):
    """Make a file path as though this file's directory is a root directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), *file_path))


class CONSTS(NamedTuple):
    """Jinja2 does not like type hinting, so they are not being written here for now."""

    TESTING = True
    autoreload = True

    db_aiosqlite = False
    db_path = make_path('/path/to/archive.db')

    db_aiomysql = True
    db_host = '192.168.0.47'
    db_port = 3306
    db_database = 'hayden'
    db_user = 'username'
    db_password = 'password'
    db_min_connections = 3
    db_max_connections = 10

    with open(make_path("secret.txt"), encoding="utf-8") as f:
        SECRET_KEY = f.read().strip()

    site_name = "Ayase Quart"
    site_url = "https://127.0.0.1:9001"

    if TESTING:
        site_host = "127.0.0.1"
        site_port = 9001
        site_url = f"http://{site_host}:{site_port}"

    key_file = None # 'key.pem'
    cert_file = None # 'cert.pem'

    site_name= 'Ayase Quart'

    board_objects = [
        {'shortname': 'ck', 'name': 'Food & Cooking'},
        {'shortname': 'mu', 'name': 'Music'},
    ]

    html_linked_target = '_self' # or '_blank' # links to 4chan will always remain '_blank'

    # If you do not have full images, set image_uri to None. Likewise for thumbnails.
    image_uri = "https://192.168.1.99:9003/static/neo/{board_shortname}/image" # must contain {board_shortname}
    thumb_uri = "/static/neo/{board_shortname}/thumb" # must contain {board_shortname}

    theme = 'tomorrow' # 'tomorrow' 'yotsuba' 'yotsuba_b' 'futaba' 'burichan' 'photon'

    search = True
    search_result_highlight = True

    # mysql, meili, manticore, typesense, lnx
    index_search_provider = 'meili'
    index_search_host = 'http://localhost:7700'.strip('/')
    index_search_auth_key = ''
    index_search_config = dict(
        headers={
            'content-type': 'application/json',
            # 'Authorization': f'Bearer {search_auth_key}',
        }
    )

    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB upload capacity
    REVERSE_PROXY = False
    SQLALCHEMY_ECHO = False

    root_dir = os.path.dirname(__file__)
    chdir_to_root = True
    static_dir = os.path.join(root_dir, "static")

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

    board_shortname_to_name = {o['shortname']: o['name'] for o in board_objects}

    board_shortnames = [board_object['shortname'] for board_object in board_objects]

    render_constants = dict(
        theme=theme,
        site_name=site_name,
        board_objects=board_objects,
        search=search,
        image_uri=image_uri,
        thumb_uri=thumb_uri,
        html_linked_target=html_linked_target,
        index_search_provider=index_search_provider,
    )

    assert not (db_aiomysql and db_aiosqlite)