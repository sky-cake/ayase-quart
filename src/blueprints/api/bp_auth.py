import quart_flask_patch

from quart import Blueprint
from moderation.auth import auth_api
from moderation.user import is_valid_creds
from configs import app_conf

from quart_schema import validate_request, validate_response
from pydantic import BaseModel
from quart_rate_limiter import rate_limit
from datetime import timedelta

bp = Blueprint("bp_api_auth", __name__, url_prefix='/api/v1')


class Credentials(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    token: str
    error: str | None


@bp.post(app_conf['login_endpoint'])
@rate_limit(3, timedelta(days=1))
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
            return Token(token=auth_api.dump_token(str(user.user_id)), error=None), 200
        return Token(token=None, error='Bad credentials'), 401
    return Token(token=None, error='Bad request'), 400
