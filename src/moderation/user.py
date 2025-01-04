from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Optional

from quart import Blueprint
from quart_auth import AuthUser, Unauthorized, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from db import db_m
from enums import DbPool

bp = Blueprint("bp_auth", __name__, template_folder="templates")


class Permissions(Enum):
    user_create = 'user_create'
    user_read = 'user_read'
    user_update = 'user_update'
    user_delete = 'user_delete'
    report_read = 'report_read'
    report_update = 'report_update'
    report_delete = 'report_delete'
    post_show = 'post_show'
    post_hide = 'post_hide'
    post_delete = 'post_delete'
    archive_stats_view = 'archive_stats_view'
    archive_latest_view = 'archive_latest_view'
    archive_configs_view = 'archive_configs_view'


class User(AuthUser):
    def __init__(self, auth_id: str):
        super().__init__(auth_id) # we use auth_id and user_id synonymously - i.e. max one session per user
        self.username: str = ''
        self.is_admin: bool = False
        self.is_active: bool = False
        self.permissions: set = set()

    async def load_user_data(self):
        if self.auth_id:
            u = await get_user_by_id(self.auth_id)
            self.username = u['username']
            self.is_admin = u['is_admin']
            self.is_active = u['is_active']
            self.permissions = u['permissions']

    def has_permissions(self, permissions: set[Permissions]) -> bool:
        return self.permissions.issuperset(permissions)


def require_is_admin(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            raise Unauthorized()
        return await func(*args, **kwargs)
    return wrapper


def require_is_active(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not current_user.is_active:
            raise Unauthorized()
        return await func(*args, **kwargs)
    return wrapper


def require_permissions(permissions: set[Permissions]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not current_user.has_permissions(permissions):
                raise Unauthorized()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_permissions_from_string(permissions: str) -> set[Permissions]:
    return set([Permissions(p) for p in permissions.split(',')]) if permissions else set()


async def get_all_users()-> Optional[list[dict]]:
    sql = """
    select
        users.*,
        group_concat(user_permissions.permission_name, ',') as permissions
    from users
    left join user_permissions using (user_id)
    group by users.user_id
    ;"""
    if not (users := await db_m.query_dict(sql, p_id=DbPool.mod)):
        return
    for user in users:
        user['permissions'] = get_permissions_from_string(user['permissions'])
    return users


async def get_user_by_id(user_id: int) -> Optional[dict]:
    sql = """
    select
        users.*,
        group_concat(user_permissions.permission_name, ',') as permissions
    from users
    left join user_permissions using (user_id)
    where user_id=∆
    group by users.user_id
    ;"""
    if not (users := await db_m.query_dict(sql, params=(user_id,), p_id=DbPool.mod)):
        return
    user = users[0]
    user['permissions'] = set([Permissions(p) for p in user['permissions'].split(',')]) if user['permissions'] else set()
    return user


async def get_user_by_username(username: str) -> Optional[dict]:
    if not (rows := await db_m.query_dict(f"select user_id from users where username=∆", params=(username,), p_id=DbPool.mod)):
        return
    return await get_user_by_id(rows[0]['user_id'])


async def create_user_if_not_exists(username: str, password: str, is_active: bool, is_admin: bool, permissions: set[Permissions],  notes: str=None):
    # username can't already exist
    if await get_user_by_username(username):
        raise ValueError(f'Username {username} already exists')

    now = datetime.now()
    params = (username, gen_pwd(password), is_active, is_admin, now, now, notes,)
    sql = f"""
    insert into users (username, password, is_active, is_admin, created_at, last_update_at, notes)
        values ({db_m.phg.size(params)})
    returning user_id
    ;"""
    rows = await db_m.query_dict(sql, params=params, commit=True, p_id=DbPool.mod)
    if not rows:
        raise ValueError(rows)
    user_id = rows[0]['user_id']

    await set_user_permissions(user_id, permissions)


async def edit_user_password_by_username(username: str, password: str):
    if not await get_user_by_username(username):
        raise ValueError(f'Username {username} already exists')

    sql = f"""
    update users
        set password=∆, last_update_at=∆
    where username=∆
    ;"""
    params = (gen_pwd(password), datetime.now(), username,)
    await db_m.query_dict(sql, params=params, commit=True, p_id=DbPool.mod)


async def set_user_permissions(user_id: int, permissions: set[Permissions]):
    print(user_id, permissions)
    sql = 'delete from user_permissions where user_id = ∆;'
    await db_m.query_dict(sql, params=(user_id,), commit=False, p_id=DbPool.mod)

    sql = 'insert into user_permissions (user_id, permission_name) values(∆, ∆);'
    for permission in permissions:
        await db_m.query_dict(sql, params=(user_id, permission.name), commit=True, p_id=DbPool.mod)


def gen_pwd(password: str) -> str:
    return generate_password_hash(password, method='scrypt', salt_length=16)


async def edit_user(user_id: int, password: str=None, is_admin: bool=False, is_active: bool=False, notes: str=None, permissions: set[Permissions]=None):
    """password is the non-hashed password"""
    if not user_id:
        raise ValueError(user_id)

    pwd = 'password=∆,' if password else ''
    sql = f"""
    update users
        set {pwd} is_admin=∆, is_active=∆, notes=∆, last_update_at=∆
    where user_id=∆
    returning user_id
    ;"""

    pwd = [gen_pwd(password)] if password else []
    params = pwd + [is_admin, is_active, notes, datetime.now(), user_id,]
    rows = await db_m.query_dict(sql, params=params, commit=True, p_id=DbPool.mod)

    if not rows:
        raise ValueError("Failed to update user")

    await set_user_permissions(int(rows[0]['user_id']), permissions)


async def set_user_active_status(user_id: int, is_active: bool):
    if not await get_user_by_id(user_id):
        raise ValueError(user_id)

    sql = """
    update users
        set is_active=∆, last_update_at=∆
    where user_id=∆
    ;"""
    params = (is_active, datetime.now(), user_id)
    await db_m.query_dict(sql, params=params, commit=True, p_id=DbPool.mod)


async def set_user_password(user_id: int, new_password: str):
    if not await get_user_by_id(user_id):
        raise ValueError(user_id)

    sql = """
    update users
        set password=∆, last_update_at=∆
    where user_id=∆
    ;"""
    params = (gen_pwd(new_password), datetime.now(), user_id,)
    await db_m.query_dict(sql, params=params, commit=True, p_id=DbPool.mod)


async def delete_user(user_id: int):
    # does not exist
    if not (await get_user_by_id(user_id)):
        raise ValueError(user_id)

    # can't delete admins
    if current_user.is_admin:
        raise PermissionError(user_id)

    await db_m.query_dict("delete from users where user_id=∆;", params=(user_id,), commit=True, p_id=DbPool.mod)


async def is_user_valid(username: str, password_candidate: str) -> Optional[dict]:
    user = await get_user_by_username(username)
    if not user:
        return

    if not check_password_hash(user.password, password_candidate):
        return

    return user
