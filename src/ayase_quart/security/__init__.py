from quart import session, request, abort
import secrets
from functools import wraps


"""
HTML forms and sources of other POST requests are responsible for including a csrf token field.
A form/csrf token must be fetched with GET before a POST can be made to alter server state/storage.
"""


# avoid confusion with wtform `csrf_token`
# if changed, also update js scripts (search for 'sct' across js files)
session_csrf_token_name = 'sct'


def get_csrf_input():
    return f'<input type="hidden" id="{session_csrf_token_name}" name="{session_csrf_token_name}" value="{session[session_csrf_token_name]}">'


async def add_csrf_token_to_session():
    if session_csrf_token_name not in session:
        session[session_csrf_token_name] = secrets.token_urlsafe(32)


def validate_csrf_token(token: str):
    if not token or token != session.get(session_csrf_token_name):
        abort(403, 'CSRF validation failed')


async def validate_csrf_token_from_form():
    form = await request.form
    token = form.get(session_csrf_token_name)
    validate_csrf_token(token)


async def validate_csrf_token_on_post():
    if request.method == 'POST':
        await validate_csrf_token_from_form()


# this is how you'd acheive applying csrf to an entire blueprint
# def apply_csrf_validation_on_bp(bp: Blueprint):
#     bp.before_request(validate_csrf_token_on_post)
#     bp.before_request(add_csrf_token_to_session)


def apply_csrf_validation_on_endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        await add_csrf_token_to_session()
        await validate_csrf_token_on_post()
        return await func(*args, **kwargs)
    return wrapper


def inject_csrf_token_to_session(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        await add_csrf_token_to_session()
        return await func(*args, **kwargs)
    return wrapper
