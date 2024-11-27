from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from db import db_m
from enums import UserRole, DbPool


async def get_all_users():
    return await db_m.query_dict("SELECT * FROM users;", p_id=DbPool.mod)


async def get_user_with_id(user_id):
    return await db_m.query_dict("SELECT * FROM users WHERE user_id=?", params=(user_id,), p_id=DbPool.mod)


async def get_user_with_username(username):
    return await db_m.query_dict("SELECT * FROM users WHERE username=?", params=(username,), p_id=DbPool.mod)


async def create_user(username: str, password: str, role: UserRole, active: bool, notes: str=None):
    if await get_user_with_username(username):
        # await flash(f'User {username} already exists. User was not created.', 'danger')
        return

    sql_string = """
    INSERT INTO users (username, password, active, role, created_datetime, last_login_datetime, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    params = (username, generate_password_hash(password, 'scrypt', 16), active, role.value, datetime.now(), datetime.now(), notes)
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def edit_user(username, password, role, active, notes):
    if not get_user_with_username(username):
        # await flash(f'User {username} does not exist. User was not modified.')
        return

    sql_string = """
    UPDATE users
    SET password=?, role=?, active=?, notes=?, last_login_datetime=?
    WHERE username=?;
    """
    params = (password, role, active, notes, datetime.now(), username)
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)
    # await flash('User updated.', 'success')


async def delete_user(user_id: int):
    if get_user_with_id(user_id):
        # await flash(f'User does not exist.', 'danger')
        return
    await db_m.query_dict("DELETE FROM users WHERE user_id=?", params=(user_id,), commit=True, p_id=DbPool.mod)


async def is_correct_password(user_record, password_candidate):
    return check_password_hash(user_record['password'], password_candidate)


async def is_user_credentials_valid(username, password_candidate):
    sql_string = """select * from users where username=?;"""

    params = (username,)
    user = await db_m.query_dict(sql_string, params=params, p_id=DbPool.mod)

    if not user or not user.username or not user.password:
        return False

    return check_password_hash(user.password, password_candidate)


async def is_user_admin(user_id):
    sql_string = """select * from users where user_id=? and role=?;"""
    params=(user_id, UserRole.admin.value)
    user = await db_m.query_dict(sql_string, params=params, p_id=DbPool.mod)

    if not user or not user.user_id or not user.password:
        return False

    return True


async def is_user_moderator(user_id):
    sql_string = """select * from users where user_id=? and role=?;"""
    params=(user_id, UserRole.moderator.value)
    user = await db_m.query_dict(sql_string, params=params, p_id=DbPool.mod)

    if not user or not user.user_id or not user.password:
        return False

    return True