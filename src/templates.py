from jinja2 import Environment, FileSystemLoader, select_autoescape
from quart import get_flashed_messages, request, url_for

from boards import board_objects
from configs import app_conf, media_conf, search_conf, site_conf
from enums import IndexSearchType
from utils import make_src_path
from utils.timestamps import ts_2_formatted

render_constants = dict(
    site_name=site_conf.get('name'),
    theme=site_conf.get('theme', 'tomorrow'),
    search=search_conf.get('enabled', False),
    index_search_host=search_conf.get('host'),
    index_search_provider=IndexSearchType(search_conf.get('provider')),
    image_uri=media_conf.get('image_uri'),
    thumb_uri=media_conf.get('thumb_uri'),
    request=request,
    url_for=url_for,
    get_flashed_messages=get_flashed_messages,
    format_ts=ts_2_formatted,
    board_objects=board_objects,
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

template_stats = env.get_template("stats.html")
template_login = env.get_template('login.html')

template_message = env.get_template("message.html")

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
template_reports_delete = env.get_template('reports/delete.html')


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
template_search_post_t = safe_env.get_template('search/post_t.html')
template_search_gallery_post_t = safe_env.get_template('search/gallery_post_t.html')
