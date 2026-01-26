from functools import wraps
from typing import Iterable

from quart import request
from quart_auth import QuartAuth
from werkzeug.local import LocalProxy

from ..configs import mod_conf
from .user import Permissions, User


# see auth_web.py for docs


auth_api = QuartAuth(
    attribute_name='auth_api_user',
    mode='bearer',
    user_class=User,
    singleton=False,
    salt     =mod_conf['auth']['bearer_salt'],
    duration =mod_conf['auth']['bearer_duration'],
)


# analogous to `quart_auth.current_web_usr`
current_api_usr = LocalProxy(lambda: auth_api.load_user())


def login_api_usr_required(func):
    @wraps(func)
    async def decorated_function(*args, **kwargs):
        bearer_token = request.headers.get('Authorization')

        if not bearer_token:
            return {'error': 'Missing Authorization header'}, 400

        if not bearer_token.startswith('bearer '):
            return {'error': 'Authorization header should be "bearer <token>"'}, 400

        token = bearer_token[7:]

        if not token:
            return {'error': 'Empty token'}, 400

        user_id = auth_api.load_token(token)
        if not user_id:
            return {'error': 'Bad token'}, 401

        kwargs['current_api_usr_id'] = int(user_id)
        return await func(*args, **kwargs)

    return decorated_function


def require_api_usr_is_admin(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not current_api_usr.is_admin:
            {'error': 'User not admin'}, 401
        return await func(*args, **kwargs)
    return wrapper


def require_api_usr_is_active(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not current_api_usr.is_active:
            {'error': 'User not active'}, 401
        return await func(*args, **kwargs)
    return wrapper


def require_api_usr_permissions(permissions: Iterable[Permissions]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not current_api_usr.has_permissions(permissions):
                {'error': 'User not permitted'}, 401
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def api_usr_authenticated(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        authenticated = False
        bearer_token = request.headers.get('Authorization', '')

        if bearer_token.lower().startswith('bearer '):
            token = bearer_token[7:]
            if token:
                user_id = auth_api.load_token(token)
                if user_id:
                    kwargs['current_api_usr_id'] = int(user_id)
                    authenticated = True

        return await func(*args, authenticated=authenticated, **kwargs)

    return wrapper
