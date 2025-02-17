import quart_flask_patch

from functools import wraps

from quart import Blueprint, current_app, flash, redirect, request, url_for
from quart_auth import Action
from forms import LoginForm
from moderation.auth import auth_web, current_web_usr
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


@bp.route("/login", methods=["GET", "POST"])
@logout_required
async def login():
    """If a user is not active, they can technically still log in/out,
    but they won't see any content."""
    form: LoginForm = await LoginForm.create_form()
    captcha = MathCaptcha(tff_file_path=current_app.config["MATH_CAPTCHA_FONT"])

    if await form.validate_on_submit():
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
            await flash("Wrong math captcha answer", "danger")

    form.captcha_id.data, form.captcha_b64_img_str = captcha.generate_captcha()

    is_authenticated = await current_web_usr.is_authenticated
    is_active = is_authenticated and current_web_usr.is_active

    if request.method == 'GET' and is_authenticated and is_active:
        return redirect(url_for('bp_web_moderation.reports_open'))

    return await render_controller(
        template_login,
        form=form,
        is_authenticated=is_authenticated,
        is_admin=is_active,
        title='Admin Login',
        tab_title='Admin Login'
    )


@bp.route("/logout", methods=["GET"])
async def logout():
    if await current_web_usr.is_authenticated:
        auth_web.logout_user()
        await flash("Logout successful.", "success")
    return redirect(url_for('bp_web_auth.login'))
