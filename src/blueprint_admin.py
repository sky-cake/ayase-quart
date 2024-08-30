from quart import (
    Blueprint,
    current_app,
    redirect,
    request,
    url_for
)

from asagi_converter import get_selector
from blueprint_auth import admin_required
from configs import CONSTS, DbType
from db.api import (
    create_user,
    delete_user,
    edit_user,
    get_all_users,
    get_user_with_id
)
from forms import UserForm
from templates import (
    template_latest,
    template_stats,
    template_users_create,
    template_users_delete,
    template_users_edit
)
from utils import render_controller

blueprint_admin = Blueprint('blueprint_admin', __name__)


placeholders = ','.join(['%s'] * len(CONSTS.boards_in_database))

if CONSTS.db_type == DbType.mysql:
    DATABASE_TABLE_STORAGE_SIZES = f"""select table_name as "Table Name", ROUND(SUM(data_length + index_length) / power(1024, 2), 1) as "Size in MB" from information_schema.tables where TABLE_SCHEMA = %s and table_name in ({placeholders}) group by table_name;"""
    DATABASE_STORAGE_SIZE = """select table_schema "DB Name", ROUND(SUM(data_length + index_length) / power(1024, 2), 1) "Size in MB" from information_schema.tables where table_schema = %(db)s group by table_schema;"""
elif CONSTS.db_type == DbType.sqlite:
    DATABASE_TABLE_STORAGE_SIZES = f"""SELECT name as "Table Name", ROUND(SUM("pgsize") / (1024. * 1024), 2) as "Size in MB" FROM "dbstat" where name in ({placeholders}) GROUP BY name;"""
    DATABASE_STORAGE_SIZE = """SELECT ROUND((page_count * page_size) / (1024.0 * 1024.0), 1) as "Size in MB" FROM pragma_page_count(), pragma_page_size();"""
else:
    raise ValueError(CONSTS.db_type)


def get_sql_latest_ops(board_shortname):
    return f"""select '{board_shortname}' as board_shortname, timestamp, num, case when title is null then '' else title end as title, comment from {board_shortname} where op=1 order by num desc limit 5;"""


def get_sql_latest_gallery(board_shortname, limit=100):
    return f"""{get_selector(board_shortname)} from {board_shortname} where media_id is not null and media_filename is not null order by timestamp desc limit {int(limit)};"""


@blueprint_admin.route("/stats")
@admin_required
async def stats():
    database_storage_size = await current_app.db.query_execute(DATABASE_STORAGE_SIZE, params={'db': CONSTS.db_database})

    if CONSTS.db_type == DbType.mysql:
        params = [CONSTS.db_database, *CONSTS.boards_in_database]
    elif CONSTS.db_type == DbType.sqlite:
        params = [*CONSTS.boards_in_database]

    database_table_storage_sizes = await current_app.db.query_execute(DATABASE_TABLE_STORAGE_SIZES, params=params)

    return await render_controller(
        template_stats,
        database_storage_size=database_storage_size,
        database_table_storage_sizes=database_table_storage_sizes,
        **CONSTS.render_constants,
        title='Stats',
        tab_title="Stats",
    )


@blueprint_admin.route("/latest")
@admin_required
async def latest():
    threads = []
    for board_shortname in CONSTS.board_shortnames:
        sql = get_sql_latest_ops(board_shortname)
        latest_ops = await current_app.db.query_execute(sql)
        threads.extend(latest_ops)

    return await render_controller(
        template_latest,
        threads=threads,
        **CONSTS.render_constants,
        title='Latest',
        tab_title="Latest",
    )


@blueprint_admin.route('/users')
@admin_required
async def users_index():
    users = get_all_users()
    return await render_controller('users/index.html', users=users)


@blueprint_admin.route('/users/<int:user_id>')
@admin_required
async def users_view(user_id):
    user = get_user_with_id(user_id)
    return await render_controller('users/view.html', user=user)


@blueprint_admin.route('/users/create', methods=['GET', 'POST'])
@admin_required
async def users_create():
    form: UserForm = await UserForm.create_form()

    if await form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        role = form.role.data
        notes = form.notes.data
        await create_user(username, password, role, notes)
        return redirect(url_for('blueprint_admin.users_index'))

    return await render_controller(
        template_users_create,
        **CONSTS.render_constants,
        title='Admin',
        tab_title='Admin',
    )


@blueprint_admin.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
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

        return redirect(url_for('blueprint_admin.users_edit', user_id=user_id))

    user = get_user_with_id(user_id)
    return await render_controller(
        template_users_edit,
        user=user,
        **CONSTS.render_constants,
        title='Admin',
        tab_title='Admin',
    )


@blueprint_admin.route('/users/<int:user_id>/delete', methods=['GET', 'POST'])
@admin_required
async def users_delete(user_id):
    if request.method == 'POST':
        await delete_user(user_id)
        return redirect(url_for('blueprint_admin.users_index'))

    return await render_controller(
        template_users_delete,
        user_id=user_id,
        **CONSTS.render_constants,
        title='Admin',
        tab_title='Admin',
    )