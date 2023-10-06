from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

env = Environment(
    loader=FileSystemLoader("./templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

# Cache templates
template_index = env.get_template("index.html")
template_board_index = env.get_template("board_index.html")
template_gallery = env.get_template("gallery.html")
template_thread = env.get_template("thread.html")
template_post = env.get_template("post.html")
template_post_sha256 = env.get_template("post_sha256.html")
template_posts = env.get_template("posts.html")
template_404 = env.get_template("404.html")
template_debug = env.get_template("debug.html")
template_stats = env.get_template("stats.html")
