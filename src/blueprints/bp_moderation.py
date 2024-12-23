from quart import Blueprint, abort, jsonify, redirect, request, url_for

from configs import mod_conf
from enums import AuthActions, ModStatus, PublicAccess
from forms import ReportModForm, ReportUserForm
from moderation.auth import auth, authorization_required
from moderation.filter_cache import fc
from moderation.report import (
    create_report,
    delete_report_if_exists,
    edit_report_if_exists,
    get_all_reports,
    get_report_by_id
)
from render import render_controller
from templates import template_reports_edit, template_reports_index
from utils.validation import validate_board
from leafs import generate_post_html


bp = Blueprint('bp_moderation', __name__)


@bp.route('/report/<string:board_shortname>/<int:thread_num>/<int:num>', methods=['POST'])
async def report(board_shortname: str, thread_num: int, num: int):
    form: ReportUserForm = await ReportUserForm.create_form(meta={'csrf': False})

    validate_board(board_shortname)

    if await form.validate_on_submit():
        report_category = form.report_category.data
        submitter_notes = form.submitter_notes.data

        op = thread_num == num
        await create_report(
            board_shortname,
            thread_num,
            num,
            op,
            request.remote_addr,
            submitter_notes,
            report_category,
            ModStatus.open,
            None,
        )
        if mod_conf['default_reported_post_public_access'] == PublicAccess.hidden:
            await fc.insert_post(board_shortname, num, op)

        return jsonify({'message': 'thank you'})
    return jsonify({'message': f'error: {form.data}: {form.errors}'})


async def formulate_reports_for_html_table(reports: list[dict]) -> list[dict]:
    """We only want a subset of report cols, and we want them formatted."""
    ds = []
    for r in reports:
        d = {}

        d['Action'] = f"""
        [
            <form class="actionform" action="{url_for('bp_moderation.reports_edit', report_id=r.report_id)}" method="get"><button class="rbtn" type="submit">View</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_id=r.report_id, action='hide')}" method="post">    <button {'disabled' if r.public_access == PublicAccess.hidden else ''} class="rbtn" type="submit">Hide</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_id=r.report_id, action='show')}" method="post">    <button {'disabled' if r.public_access == PublicAccess.visible else ''} class="rbtn" type="submit">Show</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_id=r.report_id, action='open')}" method="post">    <button {'disabled' if r.mod_status == ModStatus.open else ''} class="rbtn" type="submit">Open</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_id=r.report_id, action='close')}" method="post">   <button {'disabled' if r.mod_status == ModStatus.closed else ''} class="rbtn" type="submit">Close</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_id=r.report_id, action='delete')}" method="post">  <button class="rbtn" type="submit">Delete</button></form>
        ]"""

        d['Link'] = f'<a href="/{r.board_shortname}/thread/{r.thread_num}#p{r.num}"> /{r.board_shortname}/thread/{r.thread_num} </a>'
        d['Category'] = r.report_category
        # d['Public Access'] = 'visible' if r['public_access'] == PublicAccess.visible.value else 'hidden'
        d['Category'] = r.report_category
        d['User Note'] = r.submitter_notes
        d['Post'] = await generate_post_html(r.board_shortname, r.num)
        ds.append(d)
    return ds


def get_report_mod_status_link(mod_status: ModStatus) -> str:
    if mod_status == ModStatus.closed:
        return f'<a href="{url_for('bp_moderation.reports_open')}">Go to open reports</a>'
    return f'<a href="{url_for('bp_moderation.reports_closed')}">Go to closed reports</a>'


@bp.route('/reports/closed')
@authorization_required
async def reports_closed():
    reports = await get_all_reports(mod_status=ModStatus.closed)

    return await render_controller(
        template_reports_index,
        mod_status_link=get_report_mod_status_link(ModStatus.closed),
        reports=await formulate_reports_for_html_table(reports),
        title='Closed Reports',
        tab_title='Closed Reports',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )


@bp.route('/reports/open')
@authorization_required
async def reports_open():
    reports = await get_all_reports(mod_status=ModStatus.open)

    return await render_controller(
        template_reports_index,
        mod_status_link=get_report_mod_status_link(ModStatus.open),
        reports=await formulate_reports_for_html_table(reports),
        title='Reports',
        tab_title='Reports',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )


@bp.route('/reports/<int:report_id>/edit', methods=['GET', 'POST'])
@authorization_required
async def reports_edit(report_id: int):
    report = await get_report_by_id(report_id)
    if not report:
        return abort(404)

    form: ReportModForm = await ReportModForm.create_form()

    if (await form.validate_on_submit()) and form.is_submitted:
        public_access = form.public_access.data
        mod_status = form.mod_status.data
        moderator_notes = form.moderator_notes.data

        await edit_report_if_exists(
            report_id=report_id,
            public_access=public_access,
            mod_status=mod_status,
            title='Edit Report',
            tab_title='Edit Report',
            moderator_notes=moderator_notes,
        )
        return redirect(url_for('bp_moderation.reports_open', report_id=report_id))

    form.process(data=dict(**report))
    return await render_controller(
        template_reports_edit,
        form=form,
        report=report,
        post=await generate_post_html(report.board_shortname, report.num),
        title='Edit Report',
        tab_title='Edit Report',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )


@bp.route('/reports/<int:report_id>/<string:action>', methods=['POST'])
@authorization_required
async def reports_action(report_id: int, action: str):
    """Having this endpoint being POST-only is important."""

    if action not in ['open', 'close', 'hide', 'show', 'delete']:
        abort(404)

    report = await get_report_by_id(report_id)
    if not report:
        abort(404)

    if action == 'delete':
        report = await delete_report_if_exists(report_id)
        if report:
            await fc.delete_post(report['board_shortname'], report['num'], report['op'])
        return redirect(url_for('bp_moderation.reports_open'))

    if action == 'show':
        report = await edit_report_if_exists(report_id, public_access=PublicAccess.visible)
        await fc.delete_post(report['board_shortname'], report['num'], report['op'])
        if report['mod_status'] == ModStatus.closed:
            return redirect(url_for('bp_moderation.reports_closed'))
        return redirect(url_for('bp_moderation.reports_open'))

    if action == 'hide':
        report = await edit_report_if_exists(report_id, public_access=PublicAccess.hidden)
        if report:
            await fc.insert_post(report['board_shortname'], report['num'], report['op'])
        if report['mod_status'] == ModStatus.closed:
            return redirect(url_for('bp_moderation.reports_closed'))
        return redirect(url_for('bp_moderation.reports_open'))

    if action == 'close':
        report = await edit_report_if_exists(report_id, mod_status=ModStatus.closed)
        return redirect(url_for('bp_moderation.reports_closed'))

    if action == 'open':
        report = await edit_report_if_exists(report_id, mod_status=ModStatus.open)
        return redirect(url_for('bp_moderation.reports_open'))
