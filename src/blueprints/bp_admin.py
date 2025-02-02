import quart_flask_patch

import asyncio

from quart import Blueprint, flash, redirect, request, url_for
from quart_auth import login_required

from asagi_converter import get_selector
from boards import board_shortnames
from configs import mod_conf
from db import db_q
from enums import DbPool
from forms import UserCreateForm, UserEditForm
from moderation.user import (
    Permissions,
    create_user_if_not_exists,
    delete_user,
    edit_user,
    edit_user_password_by_username,
    get_all_users,
    get_user_by_id,
    is_valid_creds,
    load_user_data,
    require_is_active,
    require_permissions
)
from posts.template_optimizer import render_catalog_card, wrap_post_t
from render import render_controller
from templates import (
    template_catalog,
    template_configs,
    template_stats,
    template_users_create,
    template_users_delete,
    template_users_edit,
    template_users_index,
    template_users_view
)

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


@bp.route("/latest")
@login_required
@load_user_data
@require_is_active
@require_permissions([Permissions.archive_latest_view])
async def latest():
    catalog = await get_latest_ops_as_catalog()
    threads = ''.join(
        render_catalog_card(wrap_post_t(op|dict(quotelinks={})))
        for batch in catalog
        for op in batch['threads']
    )
    return await render_controller(
        template_catalog,
        threads=threads,
        title='Latest Threads',
        tab_title='Latest Threads',
        is_admin=True,
    )


@bp.route("/stats")
@login_required
@load_user_data
@require_is_active
@require_permissions([Permissions.archive_stats_view])
async def stats():
    table_row_counts = await get_row_counts()
    return await render_controller(
        template_stats,
        table_row_counts=table_row_counts,
        title='Archive Metrics',
        tab_title='Archive Metrics',
        is_admin=True,
    )


@bp.route("/configs")
@login_required
@load_user_data
@require_is_active
@require_permissions([Permissions.archive_configs_view])
async def configs():
    cs = [
        'default_reported_post_public_access',
        'hide_4chan_deleted_posts',
        'remove_replies_to_hidden_op',
        'regex_filter',
        'path_to_regex_so',
    ]
    return await render_controller(
        template_configs,
        configs=[{'key': c, 'value': mod_conf[c]} for c in cs],
        title='Archive Configs',
        tab_title='Archive Configs',
        is_admin=True,
    )


def list_to_html_ul(items: list[str], klass=None) -> str:
    klass = f'class={klass}' if klass else ''
    lis = ''.join(f'<li>{item}</li>' for item in items)
    return f"<ul {klass}>{lis}</ul>" if items else ''


@bp.route('/users')
@login_required
@load_user_data
@require_is_active
@require_permissions([Permissions.user_read])
async def users_index():
    users = await get_all_users()
    ds = []
    for u in users:
        d = {}
        d['Actions'] = f"""
            <a href="{url_for('bp_admin.users_edit', user_id=u.user_id)}">View</a> |
            <a href="{url_for('bp_admin.users_delete', user_id=u.user_id)}">Delete</a>
        """
        d['Username'] = u['username']
        d['Is Admin'] = u['is_admin']
        d['Permissions'] = list_to_html_ul(sorted([p.name for p in u['permissions']] if u['permissions'] else []), klass='disc')
        d['Active'] = 'Yes' if u['is_active'] else 'No'
        d['Notes'] = u['notes'] if u['notes'] else ''
        ds.append(d)

    return await render_controller(
        template_users_index,
        users=ds,
        is_admin=True,
        title='Users',
        tab_title='Users',
    )


@bp.route('/users/<int:user_id>')
@login_required
@load_user_data
@require_is_active
@require_permissions([Permissions.user_read])
async def users_view(user_id):
    user = await get_user_by_id(user_id)
    return await render_controller(
        template_users_view,
        user=user,
        is_admin=True,
        title='Users',
        tab_title='Users',
    )


@bp.route('/users/create', methods=['GET', 'POST'])
@require_permissions([Permissions.user_create])
async def users_create():
    form: UserCreateForm = await UserCreateForm.create_form()

    if await form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        permissions = form.permissions.data
        is_admin = form.is_admin.data
        is_active = form.is_active.data
        notes = form.notes.data
        await create_user_if_not_exists(username, password, is_active, is_admin, permissions, notes)
        return redirect(url_for('bp_admin.users_index'))

    return await render_controller(
        template_users_create,
        form=form,
        title='Create User',
        tab_title='Create User',
        is_admin=True,
    )


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@load_user_data
@require_is_active
@require_permissions([Permissions.user_update])
async def users_edit(user_id):
    form: UserEditForm = await UserEditForm.create_form()

    user = await get_user_by_id(user_id)
    if not user:
        await flash('That user does not exist.')
        redirect(url_for('bp_admin.users_index'))

    if (await form.validate_on_submit()):
        password_cur = form.password_cur.data

        if not (await is_valid_creds(user['username'], password_cur)):
            await flash('Wrong current password.')
            return redirect(url_for('bp_admin.users_edit', user_id=user_id))

        password_new = form.password_new.data
        is_admin = form.is_admin.data
        permissions = form.permissions.data
        is_active = form.is_active.data
        notes = form.notes.data

        flash_msg = await edit_user(user.get('user_id'), password=password_new, is_admin=is_admin, is_active=is_active, notes=notes, permissions=permissions)

        if password_new:
            flash_msg += ' ' + await edit_user_password_by_username(user['username'], password_new)

        await flash(flash_msg)

        return redirect(url_for('bp_admin.users_edit', user_id=user_id))

    form.is_admin.data = user.is_admin
    form.permissions.data = [p.name for p in user.permissions]
    form.is_active.data = user.is_active
    form.notes.data = user.notes
    return await render_controller(
        template_users_edit,
        form=form,
        user=user,
        title='Edit User',
        tab_title='Edit User',
        is_admin=True,
    )


@bp.route('/users/<int:user_id>/delete', methods=['GET', 'POST'])
@login_required
@load_user_data
@require_is_active
@require_permissions([Permissions.user_delete])
async def users_delete(user_id):
    if request.method == 'POST':
        flash_msg = await delete_user(user_id)
        await flash(flash_msg)
        return redirect(url_for('bp_admin.users_index'))
    
    user = await get_user_by_id(user_id)
    if not user:
        redirect(url_for('bp_admin.users_index'))

    return await render_controller(
        template_users_delete,
        user=user,
        user_id=user_id,
        title='Delete User',
        tab_title='Delete User',
        is_admin=True,
    )
