import quart_flask_patch

from quart import Blueprint, flash, redirect, request, url_for

from asagi_converter import get_row_counts, get_latest_ops_as_catalog
from boards import board_shortnames
from configs import mod_conf
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
)
from moderation.auth import (
    load_web_usr_data,
    require_web_usr_is_active,
    require_web_usr_permissions,
    login_web_usr_required,
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

bp = Blueprint('bp_web_admin', __name__)


@bp.route("/latest")
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.archive_latest_view])
async def latest():
    catalog = await get_latest_ops_as_catalog(board_shortnames)
    threads = ''.join(
        render_catalog_card(wrap_post_t(op))
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
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.archive_stats_view])
async def stats():
    table_row_counts = await get_row_counts(board_shortnames)
    return await render_controller(
        template_stats,
        table_row_counts=table_row_counts,
        title='Archive Metrics',
        tab_title='Archive Metrics',
        is_admin=True,
    )


@bp.route("/configs")
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.archive_configs_view])
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
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.user_read])
async def users_index():
    users = await get_all_users()
    ds = []
    for u in users:
        d = {}
        d['Actions'] = f"""
            <a href="{url_for('bp_web_admin.users_edit', user_id=u.user_id)}">View</a> |
            <a href="{url_for('bp_web_admin.users_delete', user_id=u.user_id)}">Delete</a>
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
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.user_read])
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
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.user_create])
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
        return redirect(url_for('bp_web_admin.users_index'))

    return await render_controller(
        template_users_create,
        form=form,
        title='Create User',
        tab_title='Create User',
        is_admin=True,
    )


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.user_update])
async def users_edit(user_id):
    form: UserEditForm = await UserEditForm.create_form()

    user = await get_user_by_id(user_id)
    if not user:
        await flash('That user does not exist.')
        redirect(url_for('bp_web_admin.users_index'))

    if (await form.validate_on_submit()):
        password_cur = form.password_cur.data

        if not (await is_valid_creds(user['username'], password_cur)):
            await flash('Bad credentials')
            return redirect(url_for('bp_web_admin.users_edit', user_id=user_id))

        password_new = form.password_new.data
        is_admin = form.is_admin.data
        permissions = form.permissions.data
        is_active = form.is_active.data
        notes = form.notes.data

        flash_msg, code = await edit_user(user.get('user_id'), password=password_new, is_admin=is_admin, is_active=is_active, notes=notes, permissions=permissions)

        await flash(flash_msg)

        return redirect(url_for('bp_web_admin.users_edit', user_id=user_id))

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
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.user_delete])
async def users_delete(user_id):
    if request.method == 'POST':
        flash_msg, code = await delete_user(user_id)
        await flash(flash_msg)
        return redirect(url_for('bp_web_admin.users_index'))

    user = await get_user_by_id(user_id)
    if not user:
        redirect(url_for('bp_web_admin.users_index'))

    return await render_controller(
        template_users_delete,
        user=user,
        user_id=user_id,
        title='Delete User',
        tab_title='Delete User',
        is_admin=True,
    )
