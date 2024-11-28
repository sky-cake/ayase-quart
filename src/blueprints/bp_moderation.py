from quart import Blueprint, redirect, request, url_for

from forms import ReportForm
from moderation.report import (
    delete_report,
    edit_report,
    get_open_reports,
    get_report_with_id
)
from render import render_controller
from templates import (
    template_reports_delete,
    template_reports_edit,
    template_reports_index,
    template_reports_view
)
from enums import AuthActions
from .bp_auth import moderator_required, auth

bp = Blueprint('bp_moderation', __name__)


@bp.route('/reports')
@moderator_required
async def reports_index():
    reports_open = get_open_reports()

    return await render_controller(
        template_reports_index,
        reports_open=reports_open,
        title='Reports',
        tab_title='Reports',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )


@bp.route('/reports/<int:report_id>')
@moderator_required
async def reports_view(report_id):
    report = get_report_with_id(report_id)

    return await render_controller(
        template_reports_view,
        report=report,
        title='Reports',
        tab_title='Reports',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )


@bp.route('/reports/<int:report_id>/edit', methods=['GET', 'POST'])
@moderator_required
async def reports_edit(report_id):
    form: ReportForm = await ReportForm.create_form()

    report = get_report_with_id(report_id)

    if report and form.validate_on_submit():
        post_no = form.post_no.data
        category = form.category.data
        details = form.details.data
        status = form.status.data
        edit_report(post_no, category, details, status)
        return redirect(url_for('bp_moderation.reports_edit', report_id=report.report_id))

    return await render_controller(
        template_reports_edit,
        report=report,
        title='Reports',
        tab_title='Reports',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )


@bp.route('/reports/<int:report_id>/delete', methods=['GET', 'POST'])
@moderator_required
async def reports_delete(report_id):
    if request.method == 'POST':
        delete_report(report_id)
        return redirect(url_for('bp_moderation.reports_index'))

    return await render_controller(
        template_reports_delete,
        report_id=report_id,
        title='Reports',
        tab_title='Reports',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )

