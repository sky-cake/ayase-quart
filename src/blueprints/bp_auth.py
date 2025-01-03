from functools import wraps

from quart import Blueprint, current_app, flash, redirect, request, url_for
from quart_auth import current_user, login_required, login_user, logout_user

from forms import LoginForm
from moderation.user import User, is_user_valid
from render import render_controller
from security.captcha import MathCaptcha
from templates import template_login

bp = Blueprint("bp_auth", __name__, template_folder="templates")


def logout_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if await current_user.is_authenticated:
            raise ValueError('Already logged in.')
        else:
            return await current_app.ensure_async(func)(*args, **kwargs)
    return wrapper


@bp.route("/login", methods=["GET", "POST"])
@logout_required
async def login():
    form: LoginForm = await LoginForm.create_form()
    captcha = MathCaptcha(tff_file_path=current_app.config["MATH_CAPTCHA_FONT"])

    if await form.validate_on_submit():
        if captcha.is_valid(form.captcha_id.data, form.captcha_answer.data):
            username = form.username.data
            password_candidate = form.password.data

            if user := await is_user_valid(username, password_candidate):
                await login_user(User(user.user_id))
                await flash("Login successful.", "success")
                return redirect(url_for("bp_moderation.reports_open"))

            await flash("Incorrect username or password.", "danger")
        await flash("Wrong math captcha answer", "danger")

    form.captcha_id.data, form.captcha_b64_img_str = captcha.generate_captcha()

    is_authenticated = await current_user.is_authenticated

    if is_authenticated and request.method == 'GET':
        return redirect(url_for('bp_moderation.reports_open'))

    return await render_controller(template_login, form=form, is_authenticated=is_authenticated, title='Admin Login', tab_title='Admin Login')


@bp.route("/logout", methods=["GET"])
@login_required
async def logout():
    await logout_user()
    await flash("Logout successful.", "success")
    return redirect(url_for("bp_auth.login"))
