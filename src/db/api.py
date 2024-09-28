import sqlite3
from datetime import datetime

from quart import flash
from werkzeug.security import check_password_hash, generate_password_hash

from configs import CONSTS, DbType
from db import fetch_tuple
from enums import DbType, UserRole


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def row_factory(cursor, data):
    keys = [col[0] for col in cursor.description]
    d = {k: v for k, v in zip(keys, data)}
    return dotdict(d)


def get_db_conn(database_path):
    conn = sqlite3.connect(database_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = row_factory
    return conn


def query_db(database_path, query, args=(), one=False, commit=False):
    conn = get_db_conn(database_path)
    cur = conn.execute(query, args)
    if commit:
        conn.commit()
        cur.close()
    else:
        results = cur.fetchall()
        cur.close()
        if results:
            if one:
                return results[0]
            return results
    return []


def get_all_users():
    return query_db(CONSTS.moderation_db_path, "SELECT * FROM users;")


def get_user_with_id(user_id):
    return query_db(CONSTS.moderation_db_path, "SELECT * FROM users WHERE user_id=?", (user_id,), one=True)


def get_user_with_username(username):
    return query_db(CONSTS.moderation_db_path, "SELECT * FROM users WHERE username=?", (username,), one=True)


async def create_user(username: str, password: str, role: UserRole, active: bool, notes: str=None):
    if get_user_with_username(username):
        await flash(f'User {username} already exists. User was not created.', 'danger')
        return

    sql_string = """
    INSERT INTO users (username, password, active, role, created_datetime, last_login_datetime, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    params = (username, generate_password_hash(password, 'scrypt', 16), active, role.value, datetime.now(), datetime.now(), notes)
    query_db(CONSTS.moderation_db_path, sql_string, params, commit=True)


async def edit_user(username, password, role, active, notes):
    if not get_user_with_username(username):
        await flash(f'User {username} does not exist. User was not modified.')
        return

    sql_string = """
    UPDATE users
    SET password=?, role=?, active=?, notes=?, last_login_datetime=?
    WHERE username=?;
    """
    params = (password, role, active, notes, datetime.now(), username)
    query_db(CONSTS.moderation_db_path, sql_string, params, commit=True)
    await flash('User updated.', 'success')


async def delete_user(user_id: int):
    if get_user_with_id(user_id):
        await flash(f'User does not exist.', 'danger')
        return
    query_db("DELETE FROM users WHERE user_id=?", (user_id,), commit=True)


def is_correct_password(user_record, password_candidate):
    return check_password_hash(user_record['password'], password_candidate)


def get_open_reports():
    sql_string = """SELECT * FROM reports WHERE status = 'open';"""
    return query_db(CONSTS.moderation_db_path, sql_string)


def delete_report(report_id):
    query_db(CONSTS.moderation_db_path, "DELETE FROM reports WHERE report_id=?", (report_id,))


def get_report_with_id(report_id):
    return query_db(CONSTS.moderation_db_path, "SELECT * FROM reports WHERE report_id=?", (report_id,), one=True)


def edit_report(post_no, category, details, status):
    sql_string = """
    UPDATE reports
    SET post_no=?, category=?, details=?, status=?, last_updated_datetime=?
    WHERE report_id=?;
    """
    params = (post_no, category, details, status, datetime.now())
    query_db(CONSTS.moderation_db_path, sql_string, params, commit=True)


def get_moderation_db():
    return sqlite3.connect(CONSTS.moderation_db_path)


async def init_moderation_db():
    with sqlite3.connect(CONSTS.moderation_db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT,
            active BOOLEAN NOT NULL DEFAULT 1,
            role TEXT NOT NULL,
            created_datetime TIMESTAMP NOT NULL,
            last_login_datetime TIMESTAMP NOT NULL,
            notes TEXT
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_no INTEGER,
            details TEXT NOT NULL,
            status TEXT NOT NULL,
            created_datetime TIMESTAMP NOT NULL,
            last_updated_datetime TIMESTAMP NOT NULL
        );
        """)
        conn.commit()

        user_count = query_db(CONSTS.moderation_db_path, 'select count(*) user_count from users;', one=True).user_count
        if not user_count:
            await create_user(CONSTS.admin_username, CONSTS.admin_password, UserRole.admin, True, 'Remember to change your default password.')
            conn.commit()
            await flash('Initial admin user created.')


async def get_db_tables() -> list[str]:
    if not hasattr(get_db_tables, 'tables'):
        match CONSTS.db_type:
            case DbType.mysql:
                sql_string = f'show tables;'
            case DbType.sqlite:
                sql_string = "SELECT name FROM sqlite_master WHERE type='table';"
            case _:
                return []
        rows = await fetch_tuple(sql_string)
        get_db_tables.tables = [row[0] for row in rows]
    return get_db_tables.tables


def is_user_credentials_valid(username, password_candidate):
    sql_string = """select * from users where username=?;"""

    params = (username,)
    user = query_db(CONSTS.moderation_db_path, sql_string, params, one=True)

    if not user or not user.username or not user.password:
        return False

    return check_password_hash(user.password, password_candidate)


def is_user_admin(user_id):
    sql_string = """select * from users where user_id=? and role=?;"""
    params=(user_id, UserRole.admin.value)
    user = query_db(CONSTS.moderation_db_path, sql_string, params, one=True)

    if not user or not user.user_id or not user.password:
        return False

    return True


def is_user_moderator(user_id):
    sql_string = """select * from users where user_id=? and role=?;"""
    params=(user_id, UserRole.moderator.value)
    user = query_db(CONSTS.moderation_db_path, sql_string, params, one=True)

    if not user or not user.user_id or not user.password:
        return False

    return True