from datetime import timedelta

from pydantic import BaseModel, Field
from quart import Blueprint, jsonify
from quart_rate_limiter import rate_limit
from quart_schema import validate_request

from asagi_converter import get_latest_ops_as_catalog
from boards import board_shortnames
from configs import mod_conf
from moderation.auth import (
    login_api_usr_required,
    require_api_usr_is_active,
    require_api_usr_permissions
)
from moderation.user import (
    Permissions,
    create_user_if_not_exists,
    delete_user,
    edit_user,
    get_all_users,
    get_user_by_id,
    is_valid_creds
)

bp = Blueprint('bp_api_admin', __name__, url_prefix='/api/v1')


@bp.get("/latest")
@login_api_usr_required
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.archive_latest_view])
async def latest(current_api_usr_id: int):
    catalog = await get_latest_ops_as_catalog(board_shortnames)
    if catalog:
        return jsonify(catalog), 200
    return {'error': 'No data found'}, 404


@bp.get("/configs")
@login_api_usr_required
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.archive_configs_view])
async def configs(current_api_usr_id: int):
    cs = [
        'hide_post_if_reported',
        'hide_4chan_deleted_posts',
        'remove_replies_to_hidden_op',
        'regex_filter',
        'path_to_regex_so',
    ]
    return jsonify([{'key': c, 'value': mod_conf[c]} for c in cs]), 200


@bp.get('/users')
@login_api_usr_required
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.user_read])
async def users_index(current_api_usr_id: int):
    users = await get_all_users()
    if users:
        return jsonify(users), 200
    return {'error': 'No users found'}, 404


@bp.get('/users/<int:user_id>')
@login_api_usr_required
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.user_read])
async def users_view(current_api_usr_id: int, user_id: int):
    user = await get_user_by_id(user_id)
    if user:
        return jsonify(user), 200
    return {'error': 'User not found'}, 404


class UserPOST(BaseModel):
    username: str
    password: str
    permissions: list[Permissions] | None = Field(description=f'Zero or more: {[x.name for x in Permissions]}')
    is_admin: bool
    is_active: bool
    notes: str | None


@bp.post('/users')
@validate_request(UserPOST)
@rate_limit(6, timedelta(hours=1))
@login_api_usr_required
@require_api_usr_permissions([Permissions.user_create])
async def users_create(data: UserPOST, current_api_usr_id: int):
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
        return {'msg': 'User created'}, 200
    return {'error': 'Bad credentials'}, 400


class UserPUT(BaseModel):
    username: str
    password_old: str | None
    password_new: str | None
    permissions: list[Permissions] | None = Field(description=f'Zero or more: {[x.name for x in Permissions]}')
    is_admin: bool
    is_active: bool
    notes: str | None


@bp.put('/users/<int:user_id>')
@validate_request(UserPUT)
@login_api_usr_required
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.user_update])
async def users_edit(data: UserPUT, current_api_usr_id: int, user_id: int):
    user = await get_user_by_id(user_id)
    if not user:
        return {'error': 'User not found'}, 404

    if data.username.strip():
        pwd = None
        if data.password_old and data.password_new:
            if not (await is_valid_creds(data.username, data.password_old)):
                return {'error': 'Bad credentials'}, 400
            pwd = data.password_new

        flash_msg, code = await edit_user(
            user_id=user_id,
            password=pwd,
            is_admin=data.is_admin,
            is_active=data.is_active,
            notes=data.notes,
            permissions=data.permissions,
        )

        if code < 400:
            return {'msg': flash_msg}, code
        return {'error': flash_msg}, code
    return {'error': 'Bad username'}, 400


@bp.delete('/users/<int:user_id>')
@login_api_usr_required
@require_api_usr_is_active
@require_api_usr_permissions([Permissions.user_delete])
async def users_delete(current_api_usr_id: int, user_id: int):
    msg, code = await delete_user(user_id)
    if code < 400:
        return {'msg': msg}, code
    return {'error': msg}, code
