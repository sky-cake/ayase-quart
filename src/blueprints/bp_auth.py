from functools import wraps

from quart import Blueprint, current_app, flash, redirect, request, url_for
from quart_auth import current_user, login_user, logout_user

from forms import LoginForm
from moderation.user import User, is_valid_creds
from render import render_controller
from security.captcha import MathCaptcha
from templates import template_login

bp = Blueprint("bp_auth", __name__, template_folder="templates")


def logout_required(func):
    """If a user is not active, they can technically still log in/out,
    but they won't see any content."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        authed = await current_user.is_authenticated
        if authed and current_user.is_active:
            return redirect(url_for('bp_moderation.reports_open'))
        elif authed and not current_user.is_active:
            return redirect(url_for('bp_app.v_index'))
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
                login_user(User(user.user_id))
                await flash("Login successful.", "success")
                return redirect(url_for("bp_moderation.reports_open"))

            await flash("Incorrect username or password.", "danger")
        else:
            await flash("Wrong math captcha answer", "danger")

    form.captcha_id.data, form.captcha_b64_img_str = captcha.generate_captcha()

    authed = current_user.is_authenticated
    valid_user = authed and current_user.is_active
    if valid_user and request.method == 'GET':
        return redirect(url_for('bp_moderation.reports_open'))

    return await render_controller(template_login, form=form, is_authenticated=valid_user, title='Admin Login', tab_title='Admin Login')


@bp.route("/logout", methods=["GET"])
async def logout():
    if await current_user.is_authenticated:
        logout_user()
        await flash("Logout successful.", "success")
    return redirect(url_for("bp_auth.login"))
