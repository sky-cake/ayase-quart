from functools import wraps

from quart import Blueprint, current_app, flash, redirect, session, url_for

from enums import AuthActions
from forms import LoginForm
from moderation.user import (
    is_user_admin,
    is_user_authority,
    is_user_moderator,
    is_user_valid
)
from render import render_controller
from security.captcha import MathCaptcha
from templates import template_login

bp = Blueprint("bp_auth", __name__, template_folder="templates")


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
                return await is_user_admin(user_id)

            return False

        if action == AuthActions.is_moderator:
            user_id = session.get("user_id", None)
            if user_id:
                return await is_user_moderator(user_id)
            return False
        
        if action == AuthActions.is_authority:
            user_id = session.get("user_id", None)
            if user_id:
                return await is_user_authority(user_id)

            return False

    raise ValueError(action, user_id)


def login_required(WRAPPED_FUNC):
    @wraps(WRAPPED_FUNC)
    async def decorated_function(*args, **kwargs):
        if not await auth(AuthActions.is_logged_in):
            await flash("Login required", "danger")
            return redirect(url_for("bp_auth.login"))
        return await WRAPPED_FUNC(*args, **kwargs)

    return decorated_function


def logout_required(WRAPPED_FUNC):
    @wraps(WRAPPED_FUNC)
    async def decorated_function(*args, **kwargs):
        if await auth(AuthActions.is_logged_in):
            await flash("Logout required", "danger")
            return redirect(url_for("bp_auth.logout"))
        return await WRAPPED_FUNC(*args, **kwargs)

    return decorated_function


def admin_required(WRAPPED_FUNC):
    @wraps(WRAPPED_FUNC)
    async def decorated_function(*args, **kwargs):
        if not await auth(AuthActions.is_admin):
            await flash("Admin permission required", "danger")
            return redirect(url_for("bp_app.v_index"))
        return await WRAPPED_FUNC(*args, **kwargs)

    return decorated_function


def authorization_required(WRAPPED_FUNC):
    @wraps(WRAPPED_FUNC)
    async def decorated_function(*args, **kwargs):
        if not await auth(AuthActions.is_authority):
            await flash("Authorization required", "danger")
            return redirect(url_for("bp_app.v_index"))
        return await WRAPPED_FUNC(*args, **kwargs)

    return decorated_function


@bp.route("/login", methods=["GET", "POST"])
async def login():
    form: LoginForm = await LoginForm.create_form()
    captcha = MathCaptcha(tff_file_path=current_app.config["MATH_CAPTCHA_FONT"])

    if await form.validate_on_submit():
        if captcha.is_valid(form.captcha_id.data, form.captcha_answer.data):
            username = form.username.data
            password_candidate = form.password.data

            if user := await is_user_valid(username, password_candidate):
                await auth(AuthActions.log_in, user_id=user.user_id)
                await flash("Login successful.", "success")
                return redirect(url_for("bp_moderation.reports_index"))


            await flash("Incorrect username or password.", "danger")
        await flash("Wrong math captcha answer", "danger")

    form.captcha_id.data, form.captcha_b64_img_str = captcha.generate_captcha()
    is_admin = await auth(AuthActions.is_admin)
    return await render_controller(template_login, form=form, is_admin=is_admin)


@bp.route("/logout", methods=["GET"])
@login_required
async def logout():
    await auth(AuthActions.log_out)
    await flash("Logout successful.", "success")
    return redirect(url_for("bp_auth.login"))
