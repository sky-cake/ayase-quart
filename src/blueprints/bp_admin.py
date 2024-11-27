from quart import Blueprint, redirect, request, url_for

from boards import board_shortnames
from db import db_q
from enums import DbType
from forms import UserForm
from moderation.user import (
    create_user,
    delete_user,
    edit_user,
    get_all_users,
    get_user_with_id
)
from render import render_controller
from templates import (
    template_latest,
    template_stats,
    template_users_create,
    template_users_delete,
    template_users_edit
)

from .bp_auth import admin_required
from configs import db_conf

bp = Blueprint('bp_admin', __name__)


placeholders = db_q.phg().size(board_shortnames)

if db_conf['db_type'] == DbType.mysql:
    DATABASE_TABLE_STORAGE_SIZES = f"""select table_name as "Table Name", ROUND(SUM(data_length + index_length) / power(1024, 2), 1) as "Size in MB" from information_schema.tables where TABLE_SCHEMA = %s and table_name in ({placeholders}) group by table_name;"""
    DATABASE_STORAGE_SIZE = """select table_schema "DB Name", ROUND(SUM(data_length + index_length) / power(1024, 2), 1) "Size in MB" from information_schema.tables where table_schema = %(db)s group by table_schema;"""
elif db_conf['db_type'] == DbType.sqlite:
    DATABASE_TABLE_STORAGE_SIZES = f"""SELECT name as "Table Name", ROUND(SUM("pgsize") / (1024. * 1024), 2) as "Size in MB" FROM "dbstat" where name in ({placeholders}) GROUP BY name;"""
    DATABASE_STORAGE_SIZE = """SELECT ROUND((page_count * page_size) / (1024.0 * 1024.0), 1) as "Size in MB" FROM pragma_page_count(), pragma_page_size();"""
else:
    raise ValueError(db_conf['db_type'])


def get_sql_latest_ops(board_shortname):
    return f"""select '{board_shortname}' as board_shortname, timestamp, num, case when title is null then '' else title end as title, comment from {board_shortname} where op=1 order by num desc limit 5;"""


@bp.route("/stats")
@admin_required
async def stats():
    database_storage_size = await db_q.query_dict(DATABASE_STORAGE_SIZE)

    if db_conf['db_type'] == DbType.mysql:
        params = [*board_shortnames]
    elif db_conf['db_type'] == DbType.sqlite:
        params = [*board_shortnames]

    database_table_storage_sizes = await db_q.query_dict(DATABASE_TABLE_STORAGE_SIZES, params=params)

    return await render_controller(
        template_stats,
        database_storage_size=database_storage_size,
        database_table_storage_sizes=database_table_storage_sizes,
        title='Stats',
        tab_title="Stats",
    )


@bp.route("/latest")
@admin_required
async def latest():
    threads = []
    for board_shortname in board_shortnames:
        sql = get_sql_latest_ops(board_shortname)
        latest_ops = await db_q.query_dict(sql)
        threads.extend(latest_ops)

    return await render_controller(
        template_latest,
        threads=threads,
        title='Latest',
        tab_title="Latest",
    )


@bp.route('/users')
@admin_required
async def users_index():
    users = get_all_users()
    return await render_controller('users/index.html', users=users)


@bp.route('/users/<int:user_id>')
@admin_required
async def users_view(user_id):
    user = get_user_with_id(user_id)
    return await render_controller('users/view.html', user=user)


@bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
async def users_create():
    form: UserForm = await UserForm.create_form()

    if await form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        role = form.role.data
        notes = form.notes.data
        await create_user(username, password, role, notes)
        return redirect(url_for('bp_admin.users_index'))

    return await render_controller(
        template_users_create,
        title='Admin',
        tab_title='Admin',
    )


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
async def users_edit(user_id):
    form: UserForm = await UserForm.create_form()

    if await form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        role = form.role.data
        active = form.active.data
        notes = form.notes.data
        await edit_user(username, password, role, active, notes)

        return redirect(url_for('bp_admin.users_edit', user_id=user_id))

    user = get_user_with_id(user_id)
    return await render_controller(
        template_users_edit,
        user=user,
        title='Admin',
        tab_title='Admin',
    )


@bp.route('/users/<int:user_id>/delete', methods=['GET', 'POST'])
@admin_required
async def users_delete(user_id):
    if request.method == 'POST':
        await delete_user(user_id)
        return redirect(url_for('bp_admin.users_index'))

    return await render_controller(
        template_users_delete,
        user_id=user_id,
        title='Admin',
        tab_title='Admin',
    )