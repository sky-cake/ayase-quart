import quart_flask_patch

from quart import Blueprint
from dataclasses import dataclass
from quart_schema import validate_request, validate_response

from asagi_converter import get_row_counts, get_latest_ops_as_catalog
from boards import board_shortnames
from configs import mod_conf
from moderation.user import (
    Permissions,
    create_user_if_not_exists,
    delete_user,
    edit_user,
    edit_user_password_by_username,
    get_all_users,
    get_user_by_id,
    is_valid_creds,
)
from moderation.auth import (
    login_api_usr_required,
    require_api_usr_is_active,
    require_api_usr_permissions
)


bp = Blueprint('bp_api_admin', __name__, url_prefix='/api/v1')


@dataclass
class Token:
    token: str


@dataclass
class User(Token):
    username: str
    password: str
    permissions: list[Permissions]
    is_admin: bool
    is_active: bool
    notes: str | None


@bp.post("/latest")
@login_api_usr_required
@validate_request(Token) # just here for api docs
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.archive_latest_view])
async def latest(data: Token, current_api_usr_id: int):
    catalog = await get_latest_ops_as_catalog(board_shortnames)
    return catalog if catalog else {'error': 'No data found'}, 404


@bp.post("/stats")
@login_api_usr_required
@validate_request(Token) # just here for api docs
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.archive_stats_view])
async def stats(data: Token, current_api_usr_id: int):
    table_row_counts = await get_row_counts(board_shortnames)
    return table_row_counts if table_row_counts else {'error': 'No info found'}, 404


@bp.post("/configs")
@login_api_usr_required
@validate_request(Token) # just here for api docs
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.archive_configs_view])
async def configs(data: Token, current_api_usr_id: int):
    cs = [
        'default_reported_post_public_access',
        'hide_4chan_deleted_posts',
        'remove_replies_to_hidden_op',
        'regex_filter',
        'path_to_regex_so',
    ]
    return [{'key': c, 'value': mod_conf[c]} for c in cs]


@bp.post('/users')
@login_api_usr_required
@validate_request(Token) # just here for api docs
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.user_read])
async def users_index(data: Token, current_api_usr_id: int):
    users = await get_all_users()
    return users if users else {'error': 'No users found'}, 404


@bp.post('/users/<int:user_id>')
@login_api_usr_required
@validate_request(Token) # just here for api docs
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.user_read])
async def users_view(data: Token, current_api_usr_id: int, user_id: int):
    user = await get_user_by_id(user_id)
    return user if user else {'error': 'User not found'}, 404


@bp.post('/users/create')
@login_api_usr_required
@validate_request(User)
@require_api_usr_permissions([Permissions.user_create])
async def users_create(data: User, current_api_usr_id: int):
    is_valid = (data.username.strip() and data.password.strip())
    if is_valid:
        await create_user_if_not_exists(
            data.username,
            data.password,
            data.is_active,
            data.is_admin,
            data.permissions,
            data.notes,
        )
        return {'msg': 'User created', 'error': None}, 200
    return {'error': 'Bad credentials'}, 400


@bp.post('/users/<int:user_id>/edit')
@login_api_usr_required
@validate_request(User)
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.user_update])
async def users_edit(data: User, current_api_usr_id: int, user_id: int):
    user = await get_user_by_id(user_id)
    if not user:
        return {'error': 'User not found'}, 404

    if data.username.strip():
        # must assume the user with the token is authorized...
        # password_cur = form.password_cur.data
        # if not (await is_valid_creds(user['username'], password_cur)):
        #     return {'error': 'Wrong current password.'}, 400

        flash_msg = await edit_user(
            user_id=user_id,
            password=data.password,
            is_admin=data.is_admin,
            is_active=data.is_active,
            notes=data.notes,
            permissions=data.permissions,
        )

        if data.password:
            flash_msg += ' ' + await edit_user_password_by_username(user['username'], data.password)

        return {'msg': flash_msg, 'error': None}, 200

    return {'error': 'Bad username'}, 400


@bp.post('/users/<int:user_id>/delete')
@login_api_usr_required
@validate_request(User)
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.user_delete])
async def users_delete(data: User, current_api_usr_id: int, user_id: int):
    flash_msg = await delete_user(user_id)
    if flash_msg:
        return {'msg': flash_msg, 'error': None}, 200
    return {'error': 'User not found'}, 404
