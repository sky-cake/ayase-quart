from functools import wraps
from typing import Iterable

from quart import current_app
from quart_auth import QuartAuth, Unauthorized
from werkzeug.local import LocalProxy

from ..configs import mod_conf
from .user import Permissions, User


# quart_auth notes

# `auth_web` and `auth_api` have methods and properties that are analogous to single quart_auth functions
# so instead of doing
# `from quart_auth import current_web_usr; current_web_usr.whatever()`
# you would do
# `current_web_usr.whatever()`

# quart_auth has a class called Action which only matters for cookies/web auth
# class Action(Enum):
#     DELETE = auto()
#     PASS = auto()
#     WRITE = auto()            # auth lasts as long as the web session
#     WRITE_PERMANENT = auto()  # auth lasts as long as the configured web duration

# see more at
# https://quart-auth.readthedocs.io/en/latest/how_to_guides/multiple_auth.html


auth_web = QuartAuth(
    attribute_name='auth_web_user',
    mode='cookie',
    singleton=False,
    user_class=User,
    cookie_samesite     =mod_conf['auth']['cookie_samesite'],
    cookie_secure       =mod_conf['auth']['cookie_secure'],
    cookie_http_only    =mod_conf['auth']['cookie_http_only'],
    cookie_name         =mod_conf['auth']['cookie_name'],
    salt                =mod_conf['auth']['cookie_salt'],
    duration            =mod_conf['auth']['cookie_duration'],
)


# analogous to `quart_auth.current_web_usr`
current_web_usr = LocalProxy(lambda: auth_web.load_user())


def login_web_usr_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not await current_web_usr.is_authenticated:
            raise Unauthorized()
        return await current_app.ensure_async(func)(*args, **kwargs)
    return wrapper


def load_web_usr_data(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        await current_web_usr.load_user()
        return await func(*args, **kwargs)
    return wrapper


def require_web_usr_is_admin(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not current_web_usr.is_admin:
            raise Unauthorized()
        return await func(*args, **kwargs)
    return wrapper


def require_web_usr_is_active(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not current_web_usr.is_active:
            raise Unauthorized()
        return await func(*args, **kwargs)
    return wrapper


def require_web_usr_permissions(permissions: Iterable[Permissions]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not current_web_usr.has_permissions(permissions):
                raise Unauthorized()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def web_usr_logged_in(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logged_in = bool(current_web_usr.auth_id)
        return await func(*args, logged_in=logged_in, **kwargs)
    return wrapper


def web_usr_is_admin(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, is_admin=bool(current_web_usr.is_admin), **kwargs)
    return wrapper
