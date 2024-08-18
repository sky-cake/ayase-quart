import sqlite3
from datetime import datetime

from quart import redirect, render_template, request, url_for, Blueprint

from configs import CONSTS
from e_nums import UserRole
from templates import template_reports_delete, template_reports_index, template_reports_edit, template_reports_view, template_users_delete, template_users_edit, template_users_index, template_users_view, template_users_create
from utils import render_controller
from blueprint_auth import moderator_required

blueprint_moderation = Blueprint('blueprint_moderation', __name__)

def get_moderation_db():
    return sqlite3.connect(CONSTS.moderation_db_path)


def init_moderation_db():
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
            preferences TEXT
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_no INTEGER,
            reason TEXT NOT NULL,
            status TEXT NOT NULL,
            created_datetime TIMESTAMP NOT NULL
        );
        """)
        conn.commit()


def users_create(username: str, password: str, role: UserRole, preferences=None):
    with sqlite3.connect(CONSTS.moderation_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO users (username, password, active, role, created_datetime, last_login_datetime, preferences)
        VALUES (?, ?, 1, ?, ?, ?, ?);
        """, (username, password, role.value, datetime.now(), datetime.now(), preferences))
        conn.commit()


def disable_user(user_id: int):
    with sqlite3.connect(CONSTS.moderation_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE users
        SET active = 0
        WHERE user_id = ?;
        """, (user_id,))
        conn.commit()


def reset_password(user_id: int, new_password: int):
    with sqlite3.connect(CONSTS.moderation_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE users
        SET password = ?
        WHERE user_id = ?;
        """, (new_password, user_id))
        conn.commit()


@blueprint_moderation.route('/users')
@moderator_required
async def users_index():
    async with get_moderation_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
    return await render_template('users/index.html', users=users)


@blueprint_moderation.route('/users/<int:user_id>')
@moderator_required
async def users_view(user_id):
    async with get_moderation_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    return await render_template('users/view.html', user=user)


@blueprint_moderation.route('/users/create', methods=['GET', 'POST'])
@moderator_required
async def users_create():
    if request.method == 'POST':
        form = await request.form
        async with get_moderation_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO users (username, password, active, role, created_datetime, last_login_datetime, preferences)
            VALUES (?, ?, 1, ?, ?, ?, ?);
            """, (
                form['username'],
                form['password'],
                form['role'],
                datetime.now(),
                datetime.now(),
                form.get('preferences', None)
            ))
            conn.commit()
        return redirect(url_for('users_index'))

    return await render_controller(
        template_users_create,
        **CONSTS.render_constants,
        title='Reports',
        tab_title='Reports',
    )


@blueprint_moderation.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@moderator_required
async def users_edit(user_id):
    async with get_moderation_db() as conn:
        cursor = conn.cursor()
        if request.method == 'POST':
            form = await request.form
            cursor.execute("""
            UPDATE users
            SET username = ?, password = ?, role = ?, active = ?, preferences = ?
            WHERE user_id = ?;
            """, (
                form['username'],
                form['password'],
                form['role'],
                1 if 'active' in form else 0,
                form.get('preferences', None),
                user_id
            ))
            conn.commit()
            return redirect(url_for('users_index'))
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    return await render_controller(
        template_users_edit,
        user=user,
        **CONSTS.render_constants,
        title='Reports',
        tab_title='Reports',
    )


@blueprint_moderation.route('/users/<int:user_id>/delete', methods=['GET', 'POST'])
@moderator_required
async def users_delete(user_id):
    if request.method == 'POST':
        async with get_moderation_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
        return redirect(url_for('users_index'))
    return await render_controller(
        template_users_delete,
        user_id=user_id,
        **CONSTS.render_constants,
        title='User Delete',
        tab_title='User Delete',
    )


@blueprint_moderation.route('/reports')
@moderator_required
async def reports_index():
    async with get_moderation_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE status = 'open';")
        reports_open = cursor.fetchall()

    return await render_controller(
        template_reports_index,
        reports_open=reports_open,
        **CONSTS.render_constants,
        title='Reports',
        tab_title='Reports',
    )


@blueprint_moderation.route('/reports/<int:report_id>')
@moderator_required
async def reports_view(report_id):
    async with get_moderation_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
        report = cursor.fetchone()
    return await render_controller(
        template_reports_view,
        report=report,
        **CONSTS.render_constants,
        title='Report View',
        tab_title='Report View',
    )


@blueprint_moderation.route('/reports/<int:report_id>/edit', methods=['GET', 'POST'])
@moderator_required
async def reports_edit(report_id):
    async with get_moderation_db() as conn:
        cursor = conn.cursor()
        if request.method == 'POST':
            form = await request.form
            cursor.execute("""
            UPDATE reports
            SET post_no = ?, reason = ?, status = ?, created_datetime = ?
            WHERE report_id = ?;
            """, (
                form['post_no'],
                form['reason'],
                form['status'],
                datetime.now(),
                report_id
            ))
            conn.commit()
            return redirect(url_for('reports_index'))
        
        cursor.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
        report = cursor.fetchone()
    return await render_controller(
        template_reports_edit,
        report=report,
        **CONSTS.render_constants,
        title='Report Edit',
        tab_title='Report Edit',
    )


@blueprint_moderation.route('/reports/<int:report_id>/delete', methods=['GET', 'POST'])
@moderator_required
async def reports_delete(report_id):
    if request.method == 'POST':
        async with get_moderation_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
            conn.commit()
        return redirect(url_for('reports_index'))

    return await render_controller(
        template_reports_delete,
        report_id=report_id,
        **CONSTS.render_constants,
        title='Report Delete',
        tab_title='Report Delete',
    )

