from jinja2 import Environment, FileSystemLoader, select_autoescape

from configs import CONSTS, make_path

env = Environment(
    loader=FileSystemLoader(make_path('templates')),
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

safe_env = Environment(
	loader=FileSystemLoader(make_path('templates')),
	auto_reload=CONSTS.autoreload,
	trim_blocks=True,
	lstrip_blocks=True,
	keep_trailing_newline=True,
	autoescape=False,
)
template_index_post = safe_env.get_template('index_search_post2.html')