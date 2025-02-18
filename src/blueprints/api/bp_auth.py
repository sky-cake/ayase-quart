import quart_flask_patch

from quart import Blueprint
from moderation.auth import auth_api
from moderation.user import is_valid_creds

from dataclasses import dataclass

from quart_schema import validate_request, validate_response


bp = Blueprint("bp_api_auth", __name__, url_prefix='/api/v1')


@dataclass
class Credentials:
    username: str
    password: str


@dataclass
class Token:
    token: str | None
    error: str | None


@bp.post('/login')
@validate_request(Credentials)
@validate_response(Token)
async def login(data: Credentials):
    """There is no token "logout". The app's secret key must be changed if you want to invalidate a token before its expiration.
    """
    username = data.username.strip()
    password = data.password.strip()

    if username and password:
        user = await is_valid_creds(username, password)
        if user:
            return Token(auth_api.dump_token(str(user.user_id)), None), 200
        return Token(None, 'Bad credentials'), 401
    return Token(None, 'Bad request'), 400
