from quart import Blueprint, current_app, flash, redirect, request, url_for

from enums import AuthActions
from forms import LoginForm
from moderation.auth import auth, login_required
from moderation.user import is_user_valid
from render import render_controller
from security.captcha import MathCaptcha
from templates import template_login

bp = Blueprint("bp_auth", __name__, template_folder="templates")


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
                return redirect(url_for("bp_moderation.reports_open"))

            await flash("Incorrect username or password.", "danger")
        await flash("Wrong math captcha answer", "danger")

    form.captcha_id.data, form.captcha_b64_img_str = captcha.generate_captcha()
    is_logged_in = await auth(AuthActions.is_logged_in)

    if is_logged_in and request.method == 'GET':
        return redirect(url_for('bp_moderation.reports_open'))

    return await render_controller(template_login, form=form, is_logged_in=is_logged_in)


@bp.route("/logout", methods=["GET"])
@login_required
async def logout():
    await auth(AuthActions.log_out)
    await flash("Logout successful.", "success")
    return redirect(url_for("bp_auth.login"))
