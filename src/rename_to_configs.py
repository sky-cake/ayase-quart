import asyncio
import os
from typing import NamedTuple

from quart import get_flashed_messages, request, url_for

from boards import get_shorts_objects, load_boards
from enums import DbType, IndexSearchType
from utils import make_src_path


class CONSTS(NamedTuple):
    """Jinja2 does not like type hinting, so they are not being written here for now."""

    TESTING = True
    autoreload = True
    validate_boards_db = True
    moderation_db_path = make_src_path('moderation.db')

    admin_username = 'admin'
    admin_password = 'admin'

    db_type = DbType.mysql  # DbType.mysql, DbType.sqlite

    db_path = make_src_path('/path/to/archive.db')  # DbType.sqlite

    db_host = '192.168.0.47'  # DbType.mysql
    db_port = 3306
    db_database = 'hayden'
    db_user = 'username'
    db_password = 'password'
    db_min_connections = 3
    db_max_connections = 10

    with open(make_src_path("secret.txt"), encoding="utf-8") as f:
        SECRET_KEY = f.read().strip()

    site_name = "Ayase Quart"
    site_url = "http://127.0.0.1:9001"

    if TESTING:
        site_host = "127.0.0.1"
        site_port = 9001
        site_url = f"http://{site_host}:{site_port}"

    key_file = None # make_src_path('key.pem')
    cert_file = None # make_src_path('cert.pem')

    site_name = 'Ayase Quart'

    boards = load_boards()
    board_shortnames, board_objects = get_shorts_objects(boards)
    boards_in_database = board_shortnames

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
    sql_echo = False

    root_dir = os.path.dirname(__file__)
    chdir_to_root = False
    static_dir = os.path.join(root_dir, "static")

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
        url_for=url_for,
        request=request,
        get_flashed_messages=get_flashed_messages,
    )

def filter_boards_in_db():
    from db.api import get_db_tables

    db_tables = asyncio.run(get_db_tables(close_pool_after=True))
    valid_boards = {t for t in db_tables if len(t) < 5} & CONSTS.boards.keys()
    removals = [board for board in CONSTS.boards if board not in valid_boards]
    CONSTS.boards_in_database = list(valid_boards)
    if removals:
        print(f'ATTENTION! Boards not found in database:\n\t[{", ".join(removals)}]\nThey will be ignored.')
        for b in removals:
            del CONSTS.boards[b]

    if not CONSTS.boards:
        raise ValueError(f'No boards to show! Configure one of {CONSTS.boards_in_database}')

    # recompute these configs
    CONSTS.board_shortnames, CONSTS.board_objects = get_shorts_objects(CONSTS.boards)
    CONSTS.render_constants['board_objects'] = CONSTS.board_objects


if CONSTS.validate_boards_db:
    filter_boards_in_db()