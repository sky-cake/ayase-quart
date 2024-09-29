from functools import wraps

from quart import Blueprint, current_app, flash, redirect, session, url_for
from werkzeug.security import check_password_hash

from captcha import MathCaptcha
from configs import CONSTS
from db.api import get_user_with_username, is_user_admin, is_user_moderator
from enums import AuthActions
from forms import LoginForm
from render import render_controller
from templates import template_login

blueprint_auth = Blueprint("blueprint_auth", __name__, template_folder="templates")


# COLUMN_LIST = "doc_id, media_id, poster_ip, num, subnum, thread_num, op, timestamp, timestamp_expired, preview_orig, preview_w, preview_h, media_filename, media_w, media_h, media_size, media_hash, media_orig, spoiler, deleted, capcode, email, name, trip, title, comment, delpass, sticky, locked, poster_hash, poster_country, exif"
# INSERT_THREAD_INTO_DELETED = "INSERT INTO {board}_deleted SELECT * FROM {board} WHERE thread_num=:thread_num;"
# DELETE_THREAD = "DELETE FROM {board} WHERE thread_num=:thread_num;"
# INSERT_POST_INTO_DELETED = "INSERT INTO {board}_deleted SELECT * FROM {board} WHERE num=:num;"
# DELETE_POST = "DELETE FROM {board} WHERE num=:num;"


async def auth(action: AuthActions, user_id=None):
    """Handles session actions."""
    async with current_app.app_context():
        if action == AuthActions.is_logged_in:
            return "user_id" in session

        if action == AuthActions.log_in and user_id:
            session["user_id"] = user_id
            return
            
        if action == AuthActions.log_out:
            session.clear()
            return

        if action == AuthActions.get_user_id:
            return session.get("user_id", None)

        if action == AuthActions.is_admin:
            user_id = session.get("user_id", None)
            if user_id:
                is_admin = is_user_admin(user_id)
                if is_admin:
                    return True
            return False

        if action == AuthActions.is_moderator:
            user_id = session.get("user_id", None)
            if user_id:
                is_admin = is_user_moderator(user_id)
                if is_admin:
                    return True
            return False

    raise ValueError(action, user_id)


def login_required(WRAPPED_FUNC):
    @wraps(WRAPPED_FUNC)
    async def decorated_function(*args, **kwargs):
        if not (await auth(AuthActions.is_logged_in)):
            await flash("Login required", "danger")
            return redirect(url_for("blueprint_auth.login"))
        return await WRAPPED_FUNC(*args, **kwargs)

    return decorated_function


def logout_required(WRAPPED_FUNC):
    @wraps(WRAPPED_FUNC)
    async def decorated_function(*args, **kwargs):
        if (await auth(AuthActions.is_admin)) or (await auth(AuthActions.is_logged_in)):
            await flash("Logout required", "danger")
            return redirect(url_for("blueprint_auth.logout"))
        return await WRAPPED_FUNC(*args, **kwargs)

    return decorated_function


def admin_required(WRAPPED_FUNC):
    @wraps(WRAPPED_FUNC)
    async def decorated_function(*args, **kwargs):
        if not (await auth(AuthActions.is_admin)):
            await flash("Admin permission required", "danger")
            return redirect(url_for("blueprint_app.v_index"))
        return await WRAPPED_FUNC(*args, **kwargs)

    return decorated_function


def moderator_required(WRAPPED_FUNC):
    @wraps(WRAPPED_FUNC)
    async def decorated_function(*args, **kwargs):
        if (not (await auth(AuthActions.is_moderator))) and (not (await auth(AuthActions.is_admin))):
            await flash("Moderator or Admin permission required", "danger")
            return redirect(url_for("blueprint_app.v_index"))
        return await WRAPPED_FUNC(*args, **kwargs)

    return decorated_function


@blueprint_auth.route("/login", methods=["GET", "POST"])
async def login():
    form: LoginForm = await LoginForm.create_form()
    captcha = MathCaptcha(tff_file_path=current_app.config["MATH_CAPTCHA_FONT"])

    if await form.validate_on_submit():
        if captcha.is_valid(form.captcha_id.data, form.captcha_answer.data):
            username = form.username.data
            password_candidate = form.password.data

            user = get_user_with_username(username)
            if user:
                if check_password_hash(user.password, password_candidate):
                    await auth(AuthActions.log_in, user_id=user.user_id)

                    await flash("Login successful.", "success")
                    return redirect(url_for("blueprint_moderation.reports_index"))

            await flash("Incorrect username or password.", "danger")
        await flash("Wrong math captcha answer", "danger")

    form.captcha_id.data, form.captcha_b64_img_str = captcha.generate_captcha()
    is_admin = await auth(AuthActions.is_admin)
    return await render_controller(template_login, form=form, **CONSTS.render_constants, is_admin=is_admin)


@blueprint_auth.route("/logout", methods=["GET"])
@login_required
async def logout():
    await auth(AuthActions.log_out)
    await flash("Logout successful.", "success")
    return redirect(url_for("blueprint_auth.login"))
