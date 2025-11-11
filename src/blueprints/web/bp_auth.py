from datetime import timedelta
from functools import wraps

from quart import Blueprint, current_app, flash, redirect, url_for
from quart_auth import Action
from quart_rate_limiter import rate_limit

from configs import app_conf
from forms import LoginForm
from moderation.auth import (
    auth_web,
    current_web_usr,
    load_web_usr_data,
    web_usr_is_admin,
    web_usr_logged_in
)
from moderation.user import User, is_valid_creds
from render import render_controller
from security.captcha import MathCaptcha
from templates import template_login


bp = Blueprint("bp_web_auth", __name__, template_folder="templates")


def logout_required(func):
    """If a user is not active, they can technically still log in/out,
    but they won't see any content."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        authed = await current_web_usr.is_authenticated
        if authed and current_web_usr.is_active:
            return redirect(url_for('bp_web_moderation.reports_open'))
        elif authed and not current_web_usr.is_active:
            return redirect(url_for('bp_web_app.v_index'))
        else:
            return await current_app.ensure_async(func)(*args, **kwargs)
    return wrapper


@bp.post(app_conf['login_endpoint'])
@rate_limit(4, timedelta(hours=1))
@logout_required
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def login_post(is_admin: bool, logged_in: bool):
    return await handle_login('POST', is_admin=is_admin, logged_in=logged_in)


@bp.get(app_conf['login_endpoint'])
@rate_limit(6, timedelta(hours=1))
@logout_required
@load_web_usr_data
@web_usr_logged_in
@web_usr_is_admin
async def login_get(is_admin: bool, logged_in: bool):
    return await handle_login('GET', is_admin=is_admin, logged_in=logged_in)


async def handle_login(method: str, is_admin: bool=False, logged_in: bool=False):
    """
    - If a user is not active, they can technically still log in/out, but they won't see any content.
    - Uses wtform csrf token
    """
    form: LoginForm = await LoginForm.create_form()
    captcha = MathCaptcha(tff_file_path=current_app.config["MATH_CAPTCHA_FONT"])

    if method == 'POST' and (await form.validate_on_submit()):
        if captcha.is_valid(form.captcha_id.data, form.captcha_answer.data):
            username = form.username.data
            password_candidate = form.password.data
            user = await is_valid_creds(username, password_candidate)
            if user:
                auth_web.login_user(User(user.user_id, Action.WRITE_PERMANENT)) # obey configured cookie duration
                await flash("Login successful.", "success")
                return redirect(url_for('bp_web_moderation.reports_open'))

            await flash("Incorrect username or password.", "danger")
        else:
            await flash("Wrong math captcha answer.", "danger")

    form.captcha_id.data, form.captcha_b64_img_str = captcha.generate_captcha()

    if method == 'GET' and logged_in:
        return redirect(url_for('bp_web_moderation.reports_open'))

    return await render_controller(
        template_login,
        form=form,
        logged_in=logged_in,
        is_admin=is_admin,
        title='Admin Login',
        tab_title='Admin Login'
    )


@bp.post("/logout")
@rate_limit(4, timedelta(hours=1))
async def logout():
    if await current_web_usr.is_authenticated:
        auth_web.logout_user()
        await flash("Logout successful.", "success")
    return redirect(url_for('bp_web_auth.login_get'))
