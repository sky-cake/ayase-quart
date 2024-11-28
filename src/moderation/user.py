from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from db import db_m
from enums import DbPool, UserRole


async def get_all_users():
    return await db_m.query_dict("SELECT * FROM users;", p_id=DbPool.mod)


async def get_user_with_id(user_id):
    return await db_m.query_dict(f"SELECT * FROM users WHERE user_id=∆", params=(user_id,), p_id=DbPool.mod)


async def get_user_with_username(username):
    return await db_m.query_dict(f"SELECT * FROM users WHERE username=∆", params=(username,), p_id=DbPool.mod)


async def create_user(username: str, password: str, role: UserRole, active: bool, notes: str=None):
    if await get_user_with_username(username):
        return

    params = (username, generate_password_hash(password, 'scrypt', 16), active, role.value, datetime.now(), datetime.now(), notes)
    sql_string = f"""
    INSERT INTO users (username, password, active, role, created_datetime, last_login_datetime, notes)
    VALUES ({db_m.phg.size(params)});
    """
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def edit_user(username, password, role, active, notes):
    if not await get_user_with_username(username):
        return

    sql_string = f"""
    UPDATE users
    SET password=∆, role=∆, active=∆, notes=∆, last_login_datetime=∆
    WHERE username=∆;
    """
    params = (password, role, active, notes, datetime.now(), username)
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def delete_user(user_id: int):
    # can't delete admins
    if not (await get_user_with_id(user_id)) or (await is_user_admin(user_id)):
        return
    await db_m.query_dict("DELETE FROM users WHERE user_id=∆", params=(user_id,), commit=True, p_id=DbPool.mod)


async def is_correct_password(user_record, password_candidate):
    return check_password_hash(user_record['password'], password_candidate)


async def is_user_credentials_valid(username, password_candidate):
    sql_string = """select * from users where username=∆;"""

    params = (username,)
    user = await db_m.query_dict(sql_string, params=params, p_id=DbPool.mod)

    if not user or not user[0].user_id or not user[0].password:
        return False

    return check_password_hash(user[0].password, password_candidate)


async def is_user_admin(user_id):
    sql_string = """select * from users where user_id=∆ and role=∆;"""
    params=(user_id, UserRole.admin.value)
    user = await db_m.query_dict(sql_string, params=params, p_id=DbPool.mod)

    if not user or not user[0].user_id or not user[0].password:
        return False

    return True


async def is_user_moderator(user_id):
    sql_string = """select * from users where user_id=∆ and role=∆;"""
    params=(user_id, UserRole.moderator.value)
    user = await db_m.query_dict(sql_string, params=params, p_id=DbPool.mod)

    if not user or not user[0].user_id or not user[0].password:
        return False

    return True