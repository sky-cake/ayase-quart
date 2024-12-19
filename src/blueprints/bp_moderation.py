from quart import Blueprint, jsonify, redirect, request, url_for

from enums import AuthActions, ReportStatus
from forms import ReportModForm, ReportUserForm
from moderation.report import (
    create_report,
    delete_report,
    edit_report,
    get_all_reports,
    get_report_by_id
)
from render import render_controller
from templates import (
    template_reports_delete,
    template_reports_edit,
    template_reports_index,
    template_reports_view
)
from utils.validation import validate_board

from .bp_auth import auth, authorization_required

bp = Blueprint('bp_moderation', __name__)

@bp.route('/report/<string:board_shortname>/<int:num>', methods=['POST'])
async def report(board_shortname: str, num: int):
    form: ReportUserForm = await ReportUserForm.create_form(meta={'csrf': False})

    validate_board(board_shortname)

    if await form.validate_on_submit():
        report_category = form.report_category.data
        submitter_notes = form.submitter_notes.data

        await create_report(
            board_shortname,
            num,
            request.remote_addr,
            submitter_notes,
            report_category,
            ReportStatus.open,
            None,
        )
        return jsonify({'message': 'thank you'})
    return jsonify({'message': f'error: {form.data}: {form.errors}'})


@bp.route('/reports')
@authorization_required
async def reports_index():
    reports = await get_all_reports()

    for r in reports:
        r['actions'] = f"""
        <a href="{url_for('bp_moderation.reports_view', report_id=r.report_id)}">View</a> |
        <a href="{url_for('bp_moderation.reports_edit', report_id=r.report_id)}">Edit</a> |
        <a href="{url_for('bp_moderation.reports_delete', report_id=r.report_id)}">Delete</a>
        """

    return await render_controller(
        template_reports_index,
        reports=reports,
        title='Reports',
        tab_title='Reports',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )


@bp.route('/reports/<int:report_id>')
@authorization_required
async def reports_view(report_id: int):
    report = await get_report_by_id(report_id)
    if not report:
        return "Report not found", 404

    return await render_controller(
        template_reports_view,
        report=[report],
        title='View Report',
        tab_title='View Report',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )


@bp.route('/reports/<int:report_id>/edit', methods=['GET', 'POST'])
@authorization_required
async def reports_edit(report_id: int):
    report = await get_report_by_id(report_id)
    if not report:
        return "Report not found", 404

    form: ReportModForm = await ReportModForm.create_form()

    if form.validate_on_submit() and form.is_submitted:
        post_status = form.post_status.data
        report_status = form.report_status.data
        moderator_notes = form.moderator_notes.data

        await edit_report(
            report_id=report_id,
            post_status=post_status,
            report_status=report_status,
            moderator_notes=moderator_notes,
        )
        return redirect(url_for('bp_moderation.reports_view', report_id=report_id))

    return await render_controller(
        template_reports_edit,
        form=form,
        report=report,
        title='Edit Report',
        tab_title='Edit Report',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )


@bp.route('/reports/<int:report_id>/delete', methods=['GET', 'POST'])
@authorization_required
async def reports_delete(report_id: int):
    report = await get_report_by_id(report_id)
    if not report:
        return "Report not found", 404

    if request.method == 'POST':
        await delete_report(report_id)
        return redirect(url_for('bp_moderation.reports_index'))

    return await render_controller(
        template_reports_delete,
        report_id=report_id,
        title='Delete Report',
        tab_title='Delete Report',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )
