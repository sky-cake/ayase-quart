import asyncio
import os
from typing import NamedTuple

from e_nums import DbType, IndexSearchType
from meta import all_4chan_boards


def make_path(*file_path):
    """Make a file path as though this file's directory is a root directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), *file_path))


class CONSTS(NamedTuple):
    """Jinja2 does not like type hinting, so they are not being written here for now."""

    TESTING = True
    autoreload = True
    moderation_db_path = make_path('moderation.db')

    admin_username = 'admin'
    admin_password = 'admin'

    db_type = DbType.mysql  # DbType.mysql, DbType.sqlite

    db_path = make_path('/path/to/archive.db')  # DbType.sqlite

    db_host = '192.168.0.47'  # DbType.mysql
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

    key_file = None # make_path('key.pem')
    cert_file = None # make_path('cert.pem')

    site_name = 'Ayase Quart'

    # You can set boards equal to a subset of all boards here
    # If you set this to `all_4chan_boards`, all boards in your DB will be available in AQ
    # boards = {
    #     'ck': 'Food & Cooking',
    #     'g': 'Technology',
    #     't': 'Torrent',
    #     'mu': 'Music',
    #     'unknown': 'Unknown',  # this board will not show up since its not a 4chan board
    # }
    boards = all_4chan_boards

    html_linked_target = '_self'  # or '_blank' # links to 4chan will always remain '_blank'

    # If you do not have full images, set image_uri to None. Likewise for thumbnails.
    image_uri = "https://192.168.0.47:9003/static/neo/{board_shortname}/image"  # must contain {board_shortname}
    thumb_uri = "/static/neo/{board_shortname}/thumb"  # must contain {board_shortname}

    theme = 'tomorrow'  # 'tomorrow' 'yotsuba' 'yotsuba_b' 'futaba' 'burichan' 'photon'

    redis_url = '' # Optional. The redis URL for rate limiting. The default is usually 'redis://localhost:6379'
    using_proxy = False # are you using nginx in front of hypercorn?

    search = True
    search_result_highlight = True
    default_result_limit = 100
    max_result_limit = 100

    index_search_provider = IndexSearchType.meili
    # If AQ and Meili, for example, run in docker containers, you might have to change this to the container IP address.
    # Get it with `sudo docker inspect $(sudo docker compose ps -q ayase_quart) | grep IPAddress`
    index_search_host = 'http://192.168.0.47:7700'
    index_search_auth_key = ''
    index_search_config = dict(
        headers={
            'content-type': 'application/json',
            # 'Authorization': f'Bearer {index_search_auth_key}',
        }
    )

    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB upload capacity
    SQLALCHEMY_ECHO = False

    root_dir = os.path.dirname(__file__)
    chdir_to_root = False
    static_dir = os.path.join(root_dir, "static")

    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##
    ## Do not touch the below code. Thank you. ##

    board_objects = [{'shortname': k, 'name': v} for k, v in boards.items()]
    board_objects = sorted(board_objects, key=lambda x: x['shortname'])

    board_shortname_to_name = {o['shortname']: o['name'] for o in board_objects}
    board_shortnames = [board_object['shortname'] for board_object in board_objects]
    boards_in_database = []  # to be populated later

    render_constants = dict(
        theme=theme,
        site_name=site_name,
        board_objects=board_objects,
        search=search,
        image_uri=image_uri,
        thumb_uri=thumb_uri,
        html_linked_target=html_linked_target,
        index_search_provider=index_search_provider,
        index_search_host=index_search_host.strip('/'),
    )


## Do not touch the below code. Thank you. ##
## Do not touch the below code. Thank you. ##
## Do not touch the below code. Thank you. ##
## Do not touch the below code. Thank you. ##

from db.api import get_boards_in_database


def remove_boards_from_configs_if_not_in_database():
    removals = []
    for board in CONSTS.boards:
        if board not in CONSTS.boards_in_database:
            print(f'ATTENTION! {board=} not found in database. It will be removed from configs.')
            removals.append(board)

    for b in removals:
        del CONSTS.boards[b]

    if not CONSTS.boards:
        raise ValueError(f'No boards to show! Configure one of {CONSTS.boards_in_database}')

    # recompute these configs
    CONSTS.board_objects = [{'shortname': b, 'name': CONSTS.boards[b]} for b in CONSTS.boards]
    CONSTS.board_shortname_to_name = {b: CONSTS.boards[b] for b in CONSTS.boards}
    CONSTS.board_shortnames = [b for b in CONSTS.boards]
    CONSTS.render_constants['board_objects'] = CONSTS.board_objects


CONSTS.boards_in_database = asyncio.run(get_boards_in_database())
remove_boards_from_configs_if_not_in_database()

CONSTS.index_search_host = CONSTS.index_search_host.strip('/')
