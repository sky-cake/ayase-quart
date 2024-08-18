from werkzeug.security import check_password_hash

from configs import CONSTS
from db import get_database_instance
from e_nums import DbType, UserRole
from meta import all_4chan_boards


async def get_boards_in_database():
    if CONSTS.db_type == DbType.mysql:
        sql_string = """select TABLE_NAME as name from information_schema.tables where TABLE_SCHEMA = %(name)s;"""
        assert CONSTS.db_database, CONSTS.db_database
        name = CONSTS.db_database

    elif CONSTS.db_type == DbType.sqlite:
        sql_string = """SELECT name FROM sqlite_master WHERE type=:name;"""
        name = 'table'

    db = get_database_instance(app_context=False)
    await db.connect()
    table_names = [row.name for row in await db.query_execute(sql_string, {'name': name})]
    await db.disconnect()

    if not table_names:
        raise ValueError('No tables found in the database.')

    boards_in_database = []
    for table_name in table_names:
        if table_name and table_name in all_4chan_boards and len(table_name) < 5:
            boards_in_database.append(table_name)
    return boards_in_database


async def is_user_credentials_valid(username, password_candidate):
    sql_string = """select * from users where username = %s;"""

    db = get_database_instance(app_context=False)
    await db.connect()
    user = await db.query_execute(sql_string, params=(username,), fetchone=True)
    await db.disconnect()

    if not user or not user.username or not user.password:
        return False

    return check_password_hash(user.password, password_candidate)


async def is_user_admin(user_id):
    sql_string = """select * from users where user_id = %s and role = %s;"""

    db = get_database_instance(app_context=False)
    await db.connect()
    user = await db.query_execute(sql_string, params=(user_id, UserRole.admin.value), fetchone=True)
    await db.disconnect()

    if not user or not user.user_id or not user.password:
        return False

    return True


async def is_user_moderator(user_id):
    sql_string = """select * from users where user_id = %s and role = %s;"""

    db = get_database_instance(app_context=False)
    await db.connect()
    user = await db.query_execute(sql_string, params=(user_id, UserRole.moderator.value), fetchone=True)
    await db.disconnect()

    if not user or not user.user_id or not user.password:
        return False

    return True