from functools import wraps

from quart import Blueprint, current_app, flash, redirect, session, url_for

from enums import AuthActions
from moderation.user import is_user_admin, is_user_authority, is_user_moderator

bp = Blueprint("bp_auth", __name__, template_folder="templates")


async def auth(action: AuthActions, user_id=None):
    """Handles session actions."""
    async with current_app.app_context():
        match action:
            case AuthActions.is_logged_in:
                return "user_id" in session

            case AuthActions.log_in if user_id:
                session["user_id"] = user_id
                return

            case AuthActions.log_out:
                session.clear()
                return

            case AuthActions.get_user_id:
                return session.get("user_id", None)

            case AuthActions.is_admin:
                user_id = session.get("user_id", None)
                if user_id:
                    return await is_user_admin(user_id)
                return False

            case AuthActions.is_moderator:
                user_id = session.get("user_id", None)
                if user_id:
                    return await is_user_moderator(user_id)
                return False

            case AuthActions.is_authority:
                user_id = session.get("user_id", None)
                if user_id:
                    return await is_user_authority(user_id)
                return False

            case _:
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
