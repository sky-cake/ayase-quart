from jinja2 import Environment, select_autoescape, PackageLoader
from quart import get_flashed_messages, request, url_for
from functools import cache

from .boards import board_objects
from .configs import (
    SITE_NAME, REPO_PKG,
    app_conf,
    archive_conf,
    index_search_conf,
    mod_conf,
    site_conf,
    stats_conf,
    vanilla_search_conf,
)
from .configs.conf_loader import load_asset_hashes
from .utils.timestamps import ts_2_formatted

@cache
def get_integrity(filename: str) -> str:
    if asset_hash := load_asset_hashes().get(filename):
        return f'integrity="{asset_hash}"'
    return ''

render_constants = dict(
    site_name=SITE_NAME,
    theme=site_conf.get('theme', 'tomorrow'),
    vanilla_search_enabled=vanilla_search_conf.get('enabled', False),
    index_search_enabled=index_search_conf.get('enabled', False),
    moderation_enabled=mod_conf['enabled'],
    stats_enabled=stats_conf['enabled'],
    endpoint=lambda: request.endpoint,
    url_for=url_for,
    custom_banner=site_conf.get('custom_banner', None),
    get_flashed_messages=get_flashed_messages,
    get_integrity=get_integrity,
    format_ts=ts_2_formatted,
    board_objects=board_objects,
    board_objects_d={b['shortname']:b for b in board_objects},
    testing=app_conf['testing'],
    canonical_host=archive_conf['canonical_host'],
    canonical_name=archive_conf['canonical_name'],
)

env = Environment(
    loader=PackageLoader(REPO_PKG),
    autoescape=select_autoescape(["html", "xml"]),
    auto_reload=app_conf.get('autoreload', True),
)
env.globals.update(render_constants)

# Cache templates
template_index = env.get_template("index.html")
template_board_index = env.get_template("board_index.html")
template_catalog = env.get_template("catalog.html")

template_about = env.get_template("about.html")

template_stats = env.get_template("stats.html")
template_login = env.get_template('login.html')
template_configs = env.get_template('configs.html')

template_error_message = env.get_template("error_message.html")

template_search_info = env.get_template('search/info.html')
template_search = env.get_template('search/search.html')

template_users_index = env.get_template('users/index.html')
template_users_view = env.get_template('users/view.html')
template_users_edit = env.get_template('users/edit.html')
template_users_delete = env.get_template('users/delete.html')
template_users_create = env.get_template('users/create.html')

template_reports_index = env.get_template('reports/index.html')
template_reports_view = env.get_template('reports/view.html')
template_reports_edit = env.get_template('reports/edit.html')


safe_env = Environment(
    loader=PackageLoader(REPO_PKG),
    auto_reload=app_conf.get('autoreload', True),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    autoescape=False,
)
safe_env.globals.update(render_constants)
template_thread = safe_env.get_template("thread.html")
