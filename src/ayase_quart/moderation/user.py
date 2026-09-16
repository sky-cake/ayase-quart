from datetime import datetime
from enum import Enum
from typing import Iterable, Optional

from quart_auth import Action, AuthUser
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import db_m

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
    if not (users := await db_m.query_dict(sql)):
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
    where user_id={db_m.Phg()()}
    group by users.user_id
    ;"""
    if not (users := await db_m.query_dict(sql, params=(user_id,))):
        return
    user = users[0]
    user['permissions'] = set([Permissions(p) for p in user['permissions'].split(',')]) if user['permissions'] else set()
    user['is_admin'] = bool(user['is_admin'])
    user['is_active'] = bool(user['is_active'])
    return user


async def get_user_by_username(username: str, include_pwd: bool=False) -> Optional[dict]:
    if not (rows := await db_m.query_dict(f"select user_id from users where username={db_m.Phg()()}", params=(username,))):
        return
    user = await get_user_by_id(rows[0]['user_id'])
    if not include_pwd:
        user['password'] = ''
    return user


async def create_user_if_not_exists(username: str, password: str, is_active: bool, is_admin: bool, permissions: Iterable[Permissions],  notes: str=None) -> str:
    # username can't already exist
    if await get_user_by_username(username):
        return f'''User not created. Username '{username}' already exists.'''

    now = datetime.now()
    params = (username, gen_pwd(password), is_active, is_admin, now, now, notes,)
    sql = f"""
    insert into users (username, password, is_active, is_admin, created_at, last_update_at, notes)
        values ({db_m.Phg().size(params)})
    returning user_id
    ;"""
    rows = await db_m.query_dict(sql, params=params, commit=True)
    if not rows:
        raise ValueError(rows)
    user_id = rows[0]['user_id']

    await set_user_permissions(user_id, permissions)
    return f'''User '{username}' created.'''


async def edit_user_password_by_username(username: str, password: str) -> str:
    if not await get_user_by_username(username):
        raise ValueError(f'Username {username} does not exist.')

    phg = db_m.Phg()
    sql = f"""
    update users
        set password={phg()}, last_update_at={phg()}
    where username={phg()}
    ;"""
    params = (gen_pwd(password), datetime.now(), username,)
    await db_m.query_dict(sql, params=params, commit=True)
    return 'Password updated.'


async def set_user_permissions(user_id: int, permissions: Iterable[Permissions]):
    sql = f'delete from user_permissions where user_id = {db_m.Phg()()};'
    await db_m.query_dict(sql, params=(user_id,), commit=False)

    if not permissions:
        return

    phg = db_m.Phg()
    sql = f'insert into user_permissions (user_id, permission_name) values({phg()}, {phg()});'
    for permission in permissions:
        await db_m.query_dict(sql, params=(user_id, permission.name), commit=True)


def gen_pwd(password: str) -> str:
    return generate_password_hash(password, method='scrypt', salt_length=16)


async def meets_active_admin_requirements(user_id: int) -> bool:
    """Must always have at least 1 active admin."""
    sql = f"""
        select count(distinct user_id) as active_admin_count
        from users
        where is_admin=1 and is_active=1 and user_id != {db_m.Phg()()}
    ;"""
    rows = await db_m.query_dict(sql, params=[user_id])
    if not rows:
        raise ValueError(rows)
    if rows[0]['active_admin_count'] == 0:
        return False
    return True


async def edit_user(user_id: int, password: str=None, is_admin: bool=False, is_active: bool=False, notes: str=None, permissions: Iterable[Permissions]=None) -> tuple[str, int]:
    """password is the non-hashed password"""
    if not user_id:
        return 'User not found', 404

    phg = db_m.Phg()

    if not is_admin or not is_active:
        if not (await meets_active_admin_requirements(user_id)):
            return 'User not updated. There must always be at least one active admin.', 403

    pwd = f'password={phg()},' if password else ''
    sql = f"""
    update users
        set {pwd} is_admin={phg()}, is_active={phg()}, notes={phg()}, last_update_at={phg()}
    where user_id={phg()}
    returning user_id
    ;"""

    pwd = [gen_pwd(password)] if password else []
    params = pwd + [is_admin, is_active, notes, datetime.now(), user_id,]
    rows = await db_m.query_dict(sql, params=params, commit=True)

    if not rows:
        raise ValueError("Failed to update user")

    await set_user_permissions(int(rows[0]['user_id']), permissions)

    return 'User updated.', 200


async def set_user_active_status(user_id: int, is_active: bool):
    if not await get_user_by_id(user_id):
        raise ValueError(user_id)

    phg = db_m.Phg()

    sql = f"""
    update users
        set is_active={phg()}, last_update_at={phg()}
    where user_id={phg()}
    ;"""
    params = (is_active, datetime.now(), user_id)
    await db_m.query_dict(sql, params=params, commit=True)


async def set_user_password(user_id: int, new_password: str):
    if not await get_user_by_id(user_id):
        raise ValueError(user_id)

    phg = db_m.Phg()
    sql = f"""
    update users
        set password={phg()}, last_update_at={phg()}
    where user_id={phg()}
    ;"""
    params = (gen_pwd(new_password), datetime.now(), user_id,)
    await db_m.query_dict(sql, params=params, commit=True)


async def delete_user(user_id: int) -> tuple[str, int]:
    # does not exist
    if not (user := await get_user_by_id(user_id)):
        return 'User not found.', 404

    if not (await meets_active_admin_requirements(user_id)):
        return 'User not deleted. There must always be at least one active admin.', 403

    await db_m.query_dict(f"delete from users where user_id={db_m.Phg()()};", params=(user_id,), commit=True)
    return f'''User '{user.username}' deleted.''', 200


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
        """We query user data from the database."""
        if not self.auth_id:
            return

        u = await get_user_by_id(self.auth_id)

        if not u:
            return

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
