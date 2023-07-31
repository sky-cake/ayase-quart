from quart import Quart, render_template, redirect, url_for
from quart_auth import (
    Unauthorized,
    AuthUser,
    current_user,
    login_required,
    login_user,
    logout_user,
    QuartAuth,
)

# from quart_schema import validate_request
from quart_rate_limiter import RateLimiter, rate_limit
import os
from forms import LoginForm
from flask_bootstrap import Bootstrap5
import aiomysql
from secrets import compare_digest
from datetime import timedelta
from loguru import logger
import configs
from db import execute_handler
from asagi_converter import (
    convert_thread,
    generate_index,
    convert_post,
    generate_gallery,
)
from templates import (
    template_debug,
    template_404,
    template_board_index,
    template_gallery,
    template_index,
    template_post,
    template_post_sha256,
    template_posts,
    template_thread,
)
from exceptions import NotFoundException, QueryException
from utils import get_board_entry

# see requirements.txt for a list of links directed to import packages' documentation


this_dir = os.path.dirname(__file__)
os.chdir(this_dir)

logger.add(
    "./logs/main.log",
    format="{time:YYYY-MM-DD at HH:mm:ss} {message}",
    level="INFO",
    rotation="15 MB",
)

app = Quart(__name__)

app.static_folder = os.path.join(this_dir, "static")
app.secret_key = configs.SECRET_KEY

QuartAuth(app)
rate_limiter = RateLimiter(app)

bootstrap = Bootstrap5()
bootstrap.init_app(app)


@app.before_serving
async def create_db_pool():
    app.db_pool = await aiomysql.create_pool(
        host=configs.database["mysql"]["host"],
        port=configs.database["mysql"]["port"],
        user=configs.database["mysql"]["user"],
        password=configs.database["mysql"]["password"],
        db=configs.database["mysql"]["db"],
        minsize=configs.database["mysql"]["min_connections"],
        maxsize=configs.database["mysql"]["max_connections"],
    )
    logger.info(f"Database pool created.")


# https://quart.palletsprojects.com/en/latest/how_to_guides/startup_shutdown.html#startup-and-shutdown
@app.after_serving
async def close_db_pool():
    app.db_pool.close()
    await app.db_pool.wait_closed()
    logger.info(f"Database pool closed.")


@app.errorhandler(Unauthorized)
async def error_handler_unauthorized(*errors: Exception):
    return redirect(url_for("login"))


@app.errorhandler(NotFoundException)
async def error_handler_not_found(*errors: Exception):
    content = template_404.render(
        **configs.render_constants,
        title=errors[0].title_window,
        title_window=errors[0].title_window,
        skin=configs.default_skin,
        status_code=404,
        mod=current_user.auth_id == configs.mod_username,
    )
    return content, 404


@app.errorhandler(QueryException)
async def error_handler_query(*errors: Exception):
    content = template_debug.render(
        **configs.render_constants,
        title=errors[0].title_window,
        title_window=errors[0].title_window,
        skin=configs.default_skin,
        status_code=500,
        mod=current_user.auth_id == configs.mod_username,
        debug_error=errors[0].debug_error
        if configs.debug_mode
        else "Database error. Try again later.",
    )
    return content, 500


@app.get("/")
async def index_html():
    return template_index.render(
        **configs.render_constants,
        title=configs.site_name,
        title_window=configs.site_name,
        skin=configs.default_skin,
        mod=current_user.auth_id == configs.mod_username,
    )


@app.get("/<string:board_name>")
async def board_html(board_name: str):
    if board_name in configs._archives or board_name in configs._boards:
        index = await generate_index(board_name, 1)

        if len(index["threads"]) > 0:
            board_description = get_board_entry(board_name)["name"]
            title = f"/{board_name}/ - {board_description}"
            content = template_board_index.render(
                **configs.render_constants,
                page_num=1,
                threads=index["threads"],
                quotelinks=[],
                board=board_name,
                mod=current_user.auth_id == configs.mod_username,
                image_uri=configs.image_location["image"].format(board_name=board_name),
                thumb_uri=configs.image_location["thumb"].format(board_name=board_name),
                title=title,
                title_window=title,
                skin=configs.default_skin,
            )
            return content
    raise NotFoundException(board_name)


@app.get(
    "/<string:board_name>/gallery",
)
async def gallery_html(board_name: str):
    if board_name in configs._archives or board_name in configs._boards:
        gallery = await generate_gallery(board_name, 1)

        board_description = get_board_entry(board_name)["name"]
        title = f"/{board_name}/ - {board_description}"
        title_window = title + " » Gallery"
        content = template_gallery.render(
            **configs.render_constants,
            gallery=gallery,
            page_num=1,
            board=board_name,
            mod=current_user.auth_id == configs.mod_username,
            image_uri=configs.image_location["image"].format(board_name=board_name),
            thumb_uri=configs.image_location["thumb"].format(board_name=board_name),
            title=title,
            title_window=title_window,
            skin=configs.default_skin,
        )
        return content
    raise NotFoundException(board_name)


@app.get(
    "/<string:board_name>/gallery/<int:page_num>",
)
async def gallery_index_html(board_name: str, page_num: int):
    if board_name in configs._archives or board_name in configs._boards:
        gallery = await generate_gallery(board_name, page_num)
        board_description = get_board_entry(board_name)["name"]
        title = f"/{board_name}/ - {board_description}"
        title_window = title + f" » Gallery Page {page_num}"
        content = template_gallery.render(
            **configs.render_constants,
            gallery=gallery,
            page_num=page_num,
            board=board_name,
            mod=current_user.auth_id == configs.mod_username,
            image_uri=configs.image_location["image"].format(board_name=board_name),
            thumb_uri=configs.image_location["thumb"].format(board_name=board_name),
            title=title,
            title_window=title_window,
            skin=configs.default_skin,
        )
        return content
    raise NotFoundException(board_name)


@app.get(
    "/<string:board_name>/page/<int:page_num>",
)
async def board_index_html(board_name: str, page_num: int):
    if board_name in configs._archives or board_name in configs._boards:
        index = await generate_index(board_name, page_num)
        if len(index["threads"]) > 0:
            board_description = get_board_entry(board_name)["name"]
            title = f"/{board_name}/ - {board_description}"
            title_window = title + f" » Page {page_num}"
            content = template_board_index.render(
                **configs.render_constants,
                page_num=page_num,
                threads=index["threads"],
                quotelinks=[],
                board=board_name,
                mod=current_user.auth_id == configs.mod_username,
                image_uri=configs.image_location["image"].format(board_name=board_name),
                thumb_uri=configs.image_location["thumb"].format(board_name=board_name),
                title=title,
                title_window=title_window,
                skin=configs.default_skin,
            )
            return content
    raise NotFoundException(board_name)


@app.get("/<string:board_name>/thread/<int:thread_id>")
async def thread_html(board_name: str, thread_id: int):
    if board_name in configs._archives or board_name in configs._boards:
        # use the existing json app function to grab the data
        thread_dict, quotelinks = await convert_thread(board_name, thread_id)

        title = f"/{board_name}/"
        try:
            # title comes from op's subject, use post id instead if not found
            subject_title = thread_dict["posts"][0]["sub"]
            board_description = get_board_entry(board_name)["name"]
            title = f"/{board_name}/ - {board_description}"
            title_window = (
                title
                + (f" - {subject_title}" if subject_title else "")
                + f" » Thread #{thread_id} - {configs.site_name}"
            )
        except IndexError:
            # no thread was returned
            raise NotFoundException(board_name)

        content = template_thread.render(
            **configs.render_constants,
            posts=thread_dict["posts"],
            quotelinks=quotelinks,
            board=board_name,
            mod=current_user.auth_id == configs.mod_username,
            image_uri=configs.image_location["image"].format(board_name=board_name),
            thumb_uri=configs.image_location["thumb"].format(board_name=board_name),
            title=title,
            title_window=title_window,
            skin=configs.default_skin,
        )
        return content
    raise NotFoundException(board_name)


@app.get("/<string:board_name>/posts/<int:thread_id>")
async def posts_html(board_name: str, thread_id: int):
    if board_name in configs._archives or board_name in configs._boards:
        thread_dict, quotelinks = await convert_thread(board_name, thread_id)

        if len(thread_dict["posts"]) > 0:
            # remove OP post
            del thread_dict["posts"][0]

            content = template_posts.render(
                **configs.render_constants,
                posts=thread_dict["posts"],
                quotelinks=quotelinks,
                board=board_name,
                image_uri=configs.image_location["image"].format(board_name=board_name),
                thumb_uri=configs.image_location["thumb"].format(board_name=board_name),
                skin=configs.default_skin,
                mod=current_user.auth_id == configs.mod_username,
            )
            return content
    raise NotFoundException(board_name)


@app.get("/<string:board_name>/post/<int:post_id>")
async def post_html(board_name: str, post_id: int):
    if board_name in configs._archives or board_name in configs._boards:
        post = await convert_post(board_name, post_id)

        # Switch to SHA256 template if hash option is set
        template = template_post
        if configs.render_constants["sha256_dirs"]:
            template = template_post_sha256

        if len(post) > 0:
            # set resto to a non zero value to prevent the template
            # from rendering OPs with the format of an OP post
            if post["resto"] == 0:
                post["resto"] = -1

            content = template.render(
                **configs.render_constants,
                post=post,
                board=board_name,
                image_uri=configs.image_location["image"].format(board_name=board_name),
                thumb_uri=configs.image_location["thumb"].format(board_name=board_name),
                skin=configs.default_skin,
                quotelink=True,
                mod=current_user.auth_id == configs.mod_username,
            )
            return content
    raise NotFoundException(board_name)


# limited to 1 request per 1 second, and a maximum of 20 per minute
@rate_limit(1, timedelta(seconds=1))
@rate_limit(25, timedelta(minutes=1))
@app.route("/login", methods=["GET", "POST"])
async def login():
    form = await LoginForm.create_form()
    if await form.validate_on_submit():
        if form.username.data == configs.mod_username and compare_digest(
            form.password.data, configs.mod_password
        ):
            login_user(AuthUser(configs.mod_username))
            logger.info("Logged in. Username: {}", configs.mod_username)
            return redirect(url_for("index_html"))

        logger.info("Incorrect credentials. Username: {}", configs.mod_username)
        form.form_errors.append("Incorrect credentials")

    return await render_template(
        "login.html",
        **configs.render_constants,
        posts="",
        quotelinks=[],
        board="",
        mod=current_user.auth_id == configs.mod_username,
        image_uri="",
        thumb_uri="",
        title=configs.site_name,
        title_window="Login",
        skin=configs.default_skin,
        form=form,
    )


@app.route("/logout")
@login_required
async def logout():
    logger.info("Logging out. Username: {}", current_user.auth_id)
    logout_user()
    return redirect(url_for("login"))


COLUMN_LIST = "doc_id, media_id, poster_ip, num, subnum, thread_num, op, timestamp, timestamp_expired, preview_orig, preview_w, preview_h, media_filename, media_w, media_h, media_size, media_hash, media_orig, spoiler, deleted, capcode, email, name, trip, title, comment, delpass, sticky, locked, poster_hash, poster_country, exif"
INSERT_THREAD_INTO_DELETED = "INSERT INTO {board}_deleted SELECT * FROM {board} WHERE thread_num=:thread_num;"
DELETE_THREAD = "DELETE FROM {board} WHERE thread_num=:thread_num;"
INSERT_POST_INTO_DELETED = "INSERT INTO {board}_deleted SELECT * FROM {board} WHERE num=:num;"
DELETE_POST = "DELETE FROM {board} WHERE num=:num;"


@app.delete("/<string:board>/thread/<int:thread_num>")
@login_required
async def delete_thread(board: str, thread_num: int):
    if board in configs._archives:
        try:
            await execute_handler(
                (INSERT_THREAD_INTO_DELETED + DELETE_THREAD).format(board=board),
                {"thread_num": thread_num},
                False,
            )
            return {"status": "success"}, 200
        except Exception as e:
            return {
                "status": "failed",
                "msg": "could not delete, sql query failed.",
                "err": f"{e}",
            }, 500
    return {"status": "failed", "msg": "no such board"}, 404


@app.delete("/<string:board>/post/<int:num>")
@login_required
async def delete_post(board: str, num: int):
    if board in configs._archives:
        try:
            await execute_handler(
                (INSERT_POST_INTO_DELETED + DELETE_POST).format(board=board),
                {"num": num},
                False,
            )
            return {"status": "success"}, 200
        except Exception as e:
            return {
                "status": "failed",
                "msg": "could not delete, sql query failed.",
                "err": f"{e}",
            }, 500
    return {"status": "failed", "msg": "no such board"}, 404


@app.get("/<string:board_name>/catalog.json")
async def gallery(board_name: str):
    if board_name in configs._archives:
        return await generate_gallery(board_name, 1)
    return {"error": 404}, 404


@app.get("/<string:board_name>/thread/<int:thread_id>.json")
async def thread(board_name: str, thread_id: int):
    if board_name in configs._archives:
        res = await convert_thread(board_name, thread_id)
        if res and len(res) > 0 and res[0].get("posts"):
            return res
    return {"error": 404}, 404


@app.get("/<string:board_name>/<int:page_num>.json")
async def board_index(board_name: str, page_num: int):
    if board_name in configs._archives:
        res = await generate_index(board_name, page_num, html=False)
        if res and res.get("threads"):
            return res
    return {"error": 404}, 404


if __name__ == "__main__":
    app.run("0.0.0.0", port=9003, debug=True, certfile="cert.pem", keyfile="key.pem")
