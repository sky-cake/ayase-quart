from jinja2 import Environment, FileSystemLoader, select_autoescape
from quart import get_flashed_messages, request, url_for

from boards import board_objects
from configs import app_conf, media_conf, site_conf, vanilla_search_conf, index_search_conf, tag_conf, archiveposting_conf, mod_conf, stats_conf
from utils import make_src_path
from utils.timestamps import ts_2_formatted

render_constants = dict(
    site_name=site_conf.get('name'),
    theme=site_conf.get('theme', 'tomorrow'),
    vanilla_search_enabled=vanilla_search_conf.get('enabled', False),
    index_search_enabled=index_search_conf.get('enabled', False),
    moderation_enabled=mod_conf['enabled'],
    stats_enabled=stats_conf['enabled'],
    tagging_enabled=tag_conf['enabled'],
    tagging_file_search_enabled=tag_conf['allow_file_search'],
    archiveposting_conf=archiveposting_conf if archiveposting_conf['enabled'] else {},
    image_uri=media_conf.get('image_uri'),
    thumb_uri=media_conf.get('thumb_uri'),
    endpoint=lambda: request.endpoint,
    url_for=url_for,
    get_flashed_messages=get_flashed_messages,
    format_ts=ts_2_formatted,
    board_objects=board_objects,
    testing=app_conf['testing'],
)

env = Environment(
    loader=FileSystemLoader(make_src_path('templates')),
    autoescape=select_autoescape(["html", "xml"]),
    auto_reload=app_conf.get('autoreload', True),
)
env.globals.update(render_constants)

# Cache templates
template_index = env.get_template("index.html")
template_board_index = env.get_template("board_index.html")
template_catalog = env.get_template("catalog.html")
template_thread = env.get_template("thread.html")

template_about = env.get_template("about.html")
template_soy = env.get_template("soy.html")

template_message = env.get_template("message.html")
template_messages = env.get_template("messages.html")
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
    loader=FileSystemLoader(make_src_path('templates')),
    auto_reload=app_conf.get('autoreload', True),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    autoescape=False,
)
safe_env.globals.update(dict(
    format_ts=ts_2_formatted,
))
