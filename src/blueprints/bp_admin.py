import asyncio

from quart import Blueprint, flash, redirect, request, url_for

from asagi_converter import get_selector
from boards import board_shortnames
from db import db_q
from enums import DbPool
from forms import UserForm
from moderation.user import (
    create_user,
    delete_user,
    edit_user_by_username,
    get_all_users,
    get_user_by_id
)
from render import render_controller
from templates import (
    template_catalog,
    template_stats,
    template_users_create,
    template_users_delete,
    template_users_edit,
    template_users_index,
    template_users_view,
)

from .bp_auth import admin_required

bp = Blueprint('bp_admin', __name__)


async def get_row_counts() -> dict:
    row_counts = []
    for table in board_shortnames:
        t, t_images = await asyncio.gather(
            db_q.query_dict(f"SELECT '{table}' as `table`, COUNT(*) as `rows` FROM {table};", p_id=DbPool.mod),
            db_q.query_dict(f"SELECT '{table}_images' as `table`, COUNT(*) as `rows` FROM {table}_images;", p_id=DbPool.mod),
        )
        t[0]['rows'] = f'{t[0]['rows']:,}'
        t_images[0]['rows'] = f'{t_images[0]['rows']:,}'
        row_counts.extend([t[0], t_images[0]])
    return row_counts


async def get_latest_ops_as_catalog():
    latest_ops = await asyncio.gather(*(
        db_q.query_dict(f"""
            {get_selector(board_shortname)}
            FROM {board_shortname}
            WHERE op = 1 
            ORDER BY num DESC 
            LIMIT 5;
        """)
        for board_shortname in board_shortnames
    ))
    return [{
        "page": 1,
        'threads': [
            l[0] | dict(nreplies='?', nimages='?')
            for l in latest_ops
        ],
    }]


@bp.route("/stats")
@admin_required
async def stats():
    table_row_counts = await get_row_counts()
    return await render_controller(
        template_stats,
        table_row_counts=table_row_counts,
        title='Stats',
        tab_title='Stats',
        is_admin=True,
    )


@bp.route("/latest")
@admin_required
async def latest():
    catalog = await get_latest_ops_as_catalog()
    return await render_controller(
        template_catalog,
        catalog=catalog,
        title='Latest Threads',
        tab_title='Latest Threads',
        is_admin=True,
    )


@bp.route('/users')
@admin_required
async def users_index():
    users = await get_all_users()
    return await render_controller(template_users_index, users=users, is_admin=True)


@bp.route('/users/<int:user_id>')
@admin_required
async def users_view(user_id):
    user = await get_user_by_id(user_id)
    return await render_controller(template_users_view, user=user, is_admin=True)


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
        form=form,
        title='Admin',
        tab_title='Admin',
        is_admin=True,
    )


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
async def users_edit(user_id):
    form: UserForm = await UserForm.create_form()

    if (await form.validate_on_submit()):
        username = form.username.data
        password = form.password.data
        role = form.role.data
        active = form.active.data
        notes = form.notes.data
        await edit_user_by_username(username, password, role, active, notes)

        return redirect(url_for('bp_admin.users_edit', user_id=user_id))

    if request.method == 'POST':
        await flash(f'Invalid form submission due to {form.errors}')

    user = await get_user_by_id(user_id)
    if not user:
        redirect(url_for('bp_admin.users_index'))

    form.username.data = user.username
    form.password.data = user.password
    form.role.data = user.role
    form.active.data = user.active
    form.notes.data = user.notes
    return await render_controller(
        template_users_edit,
        form=form,
        user=user,
        title='Admin',
        tab_title='Admin',
        is_admin=True,
    )


@bp.route('/users/<int:user_id>/delete', methods=['GET', 'POST'])
@admin_required
async def users_delete(user_id):
    if request.method == 'POST':
        await delete_user(user_id)
        return redirect(url_for('bp_admin.users_index'))
    
    user = await get_user_with_id(user_id)
    if not user:
        redirect(url_for('bp_admin.users_index'))
    user = user[0]

    user = await get_user_by_id(user_id)
    if not user:
        redirect(url_for('bp_admin.users_index'))

    return await render_controller(
        template_users_delete,
        user=user,
        user_id=user_id,
        title='Admin',
        tab_title='Admin',
        is_admin=True,
    )