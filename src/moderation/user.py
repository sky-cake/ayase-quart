from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Optional

from quart import Blueprint, abort
from quart_auth import AuthUser, current_user, login_required
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
        self._username: str = ''
        self._is_admin: bool = False
        self._is_active: bool = False
        self._permissions: set = set()

    async def load_user_data(self):
        if self.auth_id:
            u = await get_user_by_id(self.auth_id)
            self._username = u['username']
            self._is_admin = u['is_admin']
            self._is_active = u['is_active']
            self._permissions = u['permissions']    

    def has_permissions(self, permissions: set[Permissions]) -> bool:
        return self._permissions.issuperset(permissions)


def permissions_needed(permissions: set[Permissions]):
    def decorator(func):
        @wraps(func)
        @login_required
        async def wrapper(*args, **kwargs):
            if not current_user.has_permissions(permissions):
                abort(403)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

async def get_all_users()-> Optional[list[dict]]:
    if not (users := await db_m.query_dict("select * from users;", p_id=DbPool.mod)):
        return []
    return users


async def get_user_by_id(user_id: int) -> Optional[dict]:
    if not (users := await db_m.query_dict('select * from users where user_id=∆', params=(user_id,), p_id=DbPool.mod)):
        return
    return users[0]


async def get_user_by_username(username: str) -> Optional[dict]:
    if not (users := await db_m.query_dict(f"select * from users where username=∆", params=(username,), p_id=DbPool.mod)):
        return
    return users[0]


async def create_user_if_not_exists(username: str, password: str, active: bool, notes: str=None, is_admin: bool=True):
    # username can't already exist
    if await get_user_by_username(username):
        raise ValueError('Username already exists')

    now = datetime.now()
    params = (
        username,
        gen_pwd(password),
        active,
        is_admin,
        now,
        now,
        notes,
    )
    sql_string = f"""
    insert into users (username, password, active, is_admin, created_at, last_update_at, notes)
    values ({db_m.phg.size(params)})
    ;"""
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def edit_user_password_by_username(username: str, password: str):
    if not await get_user_by_username(username):
        return

    sql_string = f"""
    update users
    set password=∆, last_update_at=∆
    where username=∆
    ;"""
    params = (
        gen_pwd(password),
        datetime.now(),
        username,
    )
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def set_user_permissions(user_id: int, permissions: set[Permissions]):
    sql_delete = 'delete from user_permissions where user_id = ∆;'
    await db_m.query_dict(sql_delete, params=(user_id,), commit=False, p_id=DbPool.mod)

    sql_insert = 'insert into user_permissions (user_id, permission_name) values(∆, ∆);'
    for permission in permissions:
        await db_m.query_dict(sql_insert, params=(user_id, permission.name), commit=False, p_id=DbPool.mod)

    await db_m.commit(p_id=DbPool.mod)


def gen_pwd(password: str) -> str:
    return generate_password_hash(password, method='scrypt', salt_length=16)


async def edit_user(user_id: int, password: str=None, is_admin: bool=False, active: bool=False, notes: str=None, permissions: set[Permissions]=None):
    """password is the non-hashed password"""
    if not user_id:
        raise ValueError(user_id)

    pp = 'password=∆,' if password else ''
    sql_string = f"""
    update users
    set {pp} is_admin=∆, active=∆, notes=∆, last_update_at=∆
    where user_id=∆
    returning user_id
    ;"""
    
    pp = [gen_pwd(password)] if password else []
    params = pp + [is_admin, active, notes, datetime.now(), user_id,]
    rows = await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)

    if not rows:
        raise ValueError("Failed to update user")

    await set_user_permissions(int(rows[0]['user_id']), permissions)


async def set_user_active_status(user_id: int, active: bool):
    if not await get_user_by_id(user_id):
        return

    sql_string = """
    update users
    set active=∆, last_update_at=∆
    where user_id=∆
    ;"""
    params = (active, datetime.now(), user_id)
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def set_user_password(user_id: int, new_password: str):
    if not await get_user_by_id(user_id):
        return

    sql_string = """
    update users
    set password=∆, last_update_at=∆
    where user_id=∆
    ;"""
    params = (
        generate_password_hash(new_password, method="scrypt", salt_length=16),
        datetime.now(),
        user_id,
    )


async def delete_user(user_id: int):
    # does not exist
    if not (await get_user_by_id(user_id)):
        return

    # can't delete admins
    if (await current_user.is_admin):
        return

    await db_m.query_dict("DELETE FROM users WHERE user_id=∆", params=(user_id,), commit=True, p_id=DbPool.mod)


async def is_user_valid(username: str, password_candidate: str) -> Optional[dict]:
    if not (user := await get_user_by_username(username)):
        return

    if not check_password_hash(user.password, password_candidate):
        return

    return user
