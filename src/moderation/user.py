from datetime import datetime
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from db import db_m
from enums import DbPool, UserRole


async def get_all_users()-> Optional[list[dict]]:
    if not (users := await db_m.query_dict("SELECT * FROM users;", p_id=DbPool.mod)):
        return
    return users


async def get_user_by_id(user_id: int) -> Optional[dict]:
    if not (users := await db_m.query_dict('SELECT * FROM users WHERE user_id=∆', params=(user_id,), p_id=DbPool.mod)):
        return
    return users[0]


async def get_user_by_username(username: str) -> Optional[dict]:
    if not (users := await db_m.query_dict(f"SELECT * FROM users WHERE username=∆", params=(username,), p_id=DbPool.mod)):
        return
    return users[0]


async def create_user(username: str, password: str, role: UserRole, active: bool, notes: str=None):
    # username can't already exist
    if await get_user_by_username(username):
        return

    now = datetime.now()
    params = (
        username,
        generate_password_hash(password, method='scrypt', salt_length=16),
        active,
        role,
        now,
        now,
        notes,
    )
    sql_string = f"""
    INSERT INTO users (username, password, active, role, created_at, last_update_at, notes)
    VALUES ({db_m.phg.size(params)});
    """
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def edit_user_by_username(username: str, password: str, role: UserRole, active: bool, notes: str=None):
    if not await get_user_by_username(username):
        return

    sql_string = f"""
    UPDATE users
    SET password=∆, role=∆, active=∆, notes=∆, last_update_at=∆
    WHERE username=∆;
    """
    params = (
        generate_password_hash(password, method='scrypt', salt_length=16),
        role,
        active,
        notes,
        datetime.now(),
        username,
    )
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def edit_user_by_id(user_id: int, password: str, role: UserRole, active: bool, notes: str=None):
    if not await get_user_by_id(user_id):
        return

    sql_string = f"""
    UPDATE users
    SET password=∆, role=∆, active=∆, notes=∆, last_update_at=∆
    WHERE user_id=∆;
    """
    params = (
        generate_password_hash(password, method='scrypt', salt_length=16),
        role,
        active,
        notes,
        datetime.now(),
        user_id,
    )
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def set_user_active_status(user_id: int, active: bool):
    if not await get_user_by_id(user_id):
        return

    sql_string = """
    UPDATE users
    SET active=∆, last_update_at=∆
    WHERE user_id=∆;
    """
    params = (active, datetime.now(), user_id)
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def set_user_password(user_id: int, new_password: str):
    if not await get_user_by_id(user_id):
        return

    sql_string = """
    UPDATE users
    SET password=∆, last_update_at=∆
    WHERE user_id=∆;
    """
    params = (
        generate_password_hash(new_password, method="scrypt", salt_length=16),
        datetime.now(),
        user_id,
    )
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def delete_user(user_id: int):
    # does not exist
    if not (await get_user_by_id(user_id)):
        return
    
    # can't delete admins
    if (await is_user_admin(user_id)):
        return

    await db_m.query_dict("DELETE FROM users WHERE user_id=∆", params=(user_id,), commit=True, p_id=DbPool.mod)


async def is_user_valid(username: str, password_candidate: str) -> Optional[dict]:
    if not (user := await get_user_by_username(username)):
        return

    if not check_password_hash(user.password, password_candidate):
        return

    return user


async def is_user_admin(user_id: str) -> bool:
    if not (user := await get_user_by_id(user_id)):
        return False

    return user.role == UserRole.admin.value


async def is_user_moderator(user_id: int) -> bool:
    if not (user := await get_user_by_id(user_id)):
        return False

    return user.role == UserRole.moderator.value


async def is_user_authority(user_id: int):
    if await is_user_admin(user_id):
        return True

    return await is_user_moderator(user_id)


async def is_user_role(user_id: int, role: UserRole) -> bool:
    if not (user := await get_user_by_id(user_id)):
        return False

    return user.role == role.value


def is_valid_role(role: str) -> bool:
    return role in {r.value for r in UserRole}
