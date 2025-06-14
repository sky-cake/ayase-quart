import quart_flask_patch  # no qa

import json
from datetime import datetime
from enum import Enum
from typing import Iterable, Optional, Any

from quart_auth import AuthUser, Action
from werkzeug.security import check_password_hash, generate_password_hash
from configs import mod_conf
from db import db_m
from db.redis import get_redis
from enums import DbPool

REDIS_MOD_DB: int = mod_conf.get('redis_db', 1)

class Permissions(Enum):
    user_create = 'user_create'
    user_read = 'user_read'
    user_update = 'user_update'
    user_delete = 'user_delete'
    report_open = 'report_open'
    report_close = 'report_close'
    report_read = 'report_read'
    report_update = 'report_update'
    report_delete = 'report_delete'
    report_save_notes = 'report_save_notes'
    post_show = 'post_show'
    post_hide = 'post_hide'
    post_delete = 'post_delete'
    media_hide = 'media_hide'
    media_show = 'media_show'
    media_delete = 'media_delete'
    archive_stats_view = 'archive_stats_view'
    archive_latest_view = 'archive_latest_view'
    archive_configs_view = 'archive_configs_view'
    messages_view = 'messages_view'


async def redis_set_user_data(user_id: int, user_data: dict[str, Any], expire_seconds: int = None):
    """
    Redis does not take dict values, so we json serialize it.
    Keep that in mind when using this.
    E.g. sets will be returned as lists.
    """
    r = get_redis(REDIS_MOD_DB)

    serialized = dict()
    for key, value in user_data.items():
        v = value
        if isinstance(value, set):
            v = json.dumps([x.value if isinstance(x, Enum) else x for x in value])
        serialized[key] = v

    successes: int = await r.hset(user_id, serialized)

    if successes != len(user_data):
        raise ValueError('Not all user data entries inserted to redis.', successes, len(user_data))

    if expire_seconds:
        await r.expire(user_id, expire_seconds)


async def redis_get_user_data(user_id: int) -> dict | None:
    """
    Redis does not take dict values, so we json serialize it.
    Keep that in mind when using this.
    E.g. sets will be returned as lists.
    """
    r = get_redis(REDIS_MOD_DB)
    user_data = await r.hgetall(user_id)

    if not user_data:
        return None

    deserialized = {}
    for key, value in user_data.items():
        key = key.decode('utf-8')
        value = value.decode('utf-8')
        try:
            deserialized[key] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            deserialized[key] = value

    return deserialized


async def redis_delete_user_data(user_id: int):
    r = get_redis(REDIS_MOD_DB)
    await r.delete(user_id)


def get_permissions_from_string(permissions: str) -> set[Permissions]:
    return set([Permissions(p) for p in permissions.split(',')]) if permissions else set()


async def get_all_users(include_pwd: bool=False)-> Optional[list[dict]]:
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
        user['is_admin'] = bool(user['is_admin'])
        user['is_active'] = bool(user['is_active'])
        if not include_pwd:
            user['password'] = ''
    return users


async def get_user_by_id(user_id: int) -> Optional[dict]:
    sql = f"""
    select
        users.*,
        group_concat(user_permissions.permission_name, ',') as permissions
    from users
        left join user_permissions using (user_id)
    where user_id={db_m.phg()}
    group by users.user_id
    ;"""
    if not (users := await db_m.query_dict(sql, params=(user_id,), p_id=DbPool.mod)):
        return
    user = users[0]
    user['permissions'] = set([Permissions(p) for p in user['permissions'].split(',')]) if user['permissions'] else set()
    user['is_admin'] = bool(user['is_admin'])
    user['is_active'] = bool(user['is_active'])
    return user


async def get_user_by_username(username: str, include_pwd: bool=False) -> Optional[dict]:
    if not (rows := await db_m.query_dict(f"select user_id from users where username={db_m.phg()}", params=(username,), p_id=DbPool.mod)):
        return
    user = await get_user_by_id(rows[0]['user_id'])
    if not include_pwd:
        user['password'] = ''
    return user


async def create_user_if_not_exists(username: str, password: str, is_active: bool, is_admin: bool, permissions: Iterable[Permissions],  notes: str=None):
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


async def edit_user_password_by_username(username: str, password: str) -> str:
    if not await get_user_by_username(username):
        raise ValueError(f'Username {username} does not exist.')

    sql = f"""
    update users
        set password={db_m.phg()}, last_update_at={db_m.phg()}
    where username={db_m.phg()}
    ;"""
    params = (gen_pwd(password), datetime.now(), username,)
    await db_m.query_dict(sql, params=params, commit=True, p_id=DbPool.mod)
    return 'Password updated.'


async def set_user_permissions(user_id: int, permissions: Iterable[Permissions]):
    sql = f'delete from user_permissions where user_id = {db_m.phg()};'
    await db_m.query_dict(sql, params=(user_id,), commit=False, p_id=DbPool.mod)

    sql = f'insert into user_permissions (user_id, permission_name) values({db_m.phg()}, {db_m.phg()});'
    for permission in permissions:
        await db_m.query_dict(sql, params=(user_id, permission.name), commit=True, p_id=DbPool.mod)


def gen_pwd(password: str) -> str:
    return generate_password_hash(password, method='scrypt', salt_length=16)


async def meets_active_admin_requirements() -> bool:
    """Must always have at least 1 active admin."""
    sql = """
        select count(*) as active_admin_count
        from users
        where is_admin=1 and is_active=1
    ;"""
    rows = await db_m.query_dict(sql, p_id=DbPool.mod)
    if not rows:
        raise ValueError(rows)
    if rows[0]['active_admin_count'] < 2:
        return False
    return True


async def edit_user(user_id: int, password: str=None, is_admin: bool=False, is_active: bool=False, notes: str=None, permissions: Iterable[Permissions]=None) -> tuple[str, int]:
    """password is the non-hashed password"""
    if not user_id:
        return 'User not found', 404

    phg = db_m.phg()

    if not is_admin or not is_active:
        if not (await meets_active_admin_requirements()):
            return 'User not update. There must always be at least one active admin.', 403

    pwd = f'password={phg},' if password else ''
    sql = f"""
    update users
        set {pwd} is_admin={phg}, is_active={phg}, notes={phg}, last_update_at={phg}
    where user_id={phg}
    returning user_id
    ;"""

    pwd = [gen_pwd(password)] if password else []
    params = pwd + [is_admin, is_active, notes, datetime.now(), user_id,]
    rows = await db_m.query_dict(sql, params=params, commit=True, p_id=DbPool.mod)

    if not rows:
        raise ValueError("Failed to update user")

    await set_user_permissions(int(rows[0]['user_id']), permissions)

    return 'User updated.', 200


async def set_user_active_status(user_id: int, is_active: bool):
    if not await get_user_by_id(user_id):
        raise ValueError(user_id)

    phg = db_m.phg()

    sql = f"""
    update users
        set is_active={phg}, last_update_at={phg}
    where user_id={phg}
    ;"""
    params = (is_active, datetime.now(), user_id)
    await db_m.query_dict(sql, params=params, commit=True, p_id=DbPool.mod)


async def set_user_password(user_id: int, new_password: str):
    if not await get_user_by_id(user_id):
        raise ValueError(user_id)

    phg = db_m.phg()
    sql = f"""
    update users
        set password={phg}, last_update_at={phg}
    where user_id={phg}
    ;"""
    params = (gen_pwd(new_password), datetime.now(), user_id,)
    await db_m.query_dict(sql, params=params, commit=True, p_id=DbPool.mod)


async def delete_user(user_id: int) -> tuple[str, int]:
    # does not exist
    if not (await get_user_by_id(user_id)):
        return 'User not found', 404

    if not (await meets_active_admin_requirements()):
        return 'User not deleted. There must always be at least one active admin.', 403

    await db_m.query_dict(f"delete from users where user_id={db_m.phg()};", params=(user_id,), commit=True, p_id=DbPool.mod)
    return 'User deleted', 200


async def is_valid_creds(username: str, password_candidate: str) -> Optional[dict]:
    user = await get_user_by_username(username, include_pwd=True)
    if not user:
        return
    if not check_password_hash(user.password, password_candidate):
        return
    user['password'] = ''
    return user


class User(AuthUser):
    def __init__(self, auth_id: str, action: Action = Action.PASS):
        super().__init__(auth_id, action) # we use auth_id and user_id synonymously - i.e. max one session per user
        self.username: str = ''
        self.is_admin: bool = False
        self.is_active: bool = False
        self.permissions: set = set()

    async def load_user(self, expire_seconds: int = 10):
        """We query user data from the database, and, if configured, cache it in redis for `expire_seconds`."""
        if not self.auth_id:
            return

        u = None
        if mod_conf['redis']:
            u = await redis_get_user_data(self.auth_id) # could not exist, or possibly be expired

        if not u:
            u = await get_user_by_id(self.auth_id)

            if mod_conf['redis']:
                key = self.auth_id
                val = {k: u[k] for k in ['username', 'is_admin', 'is_active', 'permissions']}
                await redis_set_user_data(key, val, expire_seconds)

        if not u:
            return None

        self.username = u['username']
        self.is_admin = u['is_admin']
        self.is_active = u['is_active']
        self.permissions = set(u['permissions']) # must Set() this here


    def has_permissions(self, perms: Iterable[Permissions]) -> bool:
        """Admins get to do everything, and don't have their permissions checked."""
        if self.is_admin:
            return True
        if not isinstance(perms, set):
            return self.permissions.issuperset(set(perms))
        return self.permissions.issuperset(perms)
