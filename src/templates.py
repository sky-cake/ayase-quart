from jinja2 import Environment, FileSystemLoader, select_autoescape

from configs import CONSTS
from utils import make_src_path
from utils.timestamps import ts_2_formatted

env = Environment(
    loader=FileSystemLoader(make_src_path('templates')),
    autoescape=select_autoescape(["html", "xml"]),
    auto_reload=CONSTS.autoreload,
)
env.globals.update(CONSTS.render_constants)

# Cache templates
template_index = env.get_template("index.html")
template_board_index = env.get_template("board_index.html")
template_catalog = env.get_template("catalog.html")
template_thread = env.get_template("thread.html")
template_post = env.get_template("post.html")
template_posts = env.get_template("posts.html")
template_stats = env.get_template("stats.html")
template_error_404 = env.get_template("error_404.html")
template_search = env.get_template("search.html")
template_latest = env.get_template('latest.html')
template_index_search_config = env.get_template('index_search_config.html')
template_index_search = env.get_template('index_search.html')
template_login = env.get_template('login.html')

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
    auto_reload=CONSTS.autoreload,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    autoescape=False,
)
safe_env.globals.update(dict(
    format_ts=ts_2_formatted,
))
template_index_search_post_t = safe_env.get_template('index_search_post_t.html')
template_index_search_gallery_post_t = safe_env.get_template('index_search_gallery_post_t.html')
