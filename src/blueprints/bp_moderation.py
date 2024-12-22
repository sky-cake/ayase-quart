from quart import Blueprint, jsonify, redirect, request, url_for

from asagi_converter import is_post_op
from configs import mod_conf
from enums import AuthActions, PostStatus, ReportStatus
from forms import ReportModForm, ReportUserForm
from moderation.auth import auth, authorization_required
from moderation.filter_cache import fc
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
            ReportStatus.open,
            None,
        )
        if mod_conf['default_reported_post_status'] == PostStatus.hidden:
            await fc.insert_post(board_shortname, num, op)

        return jsonify({'message': 'thank you'})
    return jsonify({'message': f'error: {form.data}: {form.errors}'})


@bp.route('/reports')
@authorization_required
async def reports_index():
    reports = await get_all_reports()

    ds = []
    for r in reports:
        d = {}

        d['Actions'] = f"""
        <a href="{url_for('bp_moderation.reports_edit', report_id=r.report_id)}">View</a> |
        <a href="{url_for('bp_moderation.reports_delete', report_id=r.report_id)}">Delete</a>
        """

        d['Link'] = f'<a href="/{r.board_shortname}/thread/{r.thread_num}#p{r.num}">Visit</a>'
        d['Category'] = r.report_category
        d['Public Access'] = 'visible' if r['post_status'] == PostStatus.visible.value else 'hidden'
        d['Mod Status'] = 'open' if r['report_status'] == ReportStatus.open.value else 'closed'
        d['User Notes'] = r.submitter_notes
        ds.append(d)

    return await render_controller(
        template_reports_index,
        reports=ds,
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
        return "Report not found", 404

    form: ReportModForm = await ReportModForm.create_form()

    if (await form.validate_on_submit()) and form.is_submitted:
        post_status = form.post_status.data
        report_status = form.report_status.data
        moderator_notes = form.moderator_notes.data

        await edit_report(
            report_id=report_id,
            post_status=post_status,
            report_status=report_status,
            moderator_notes=moderator_notes,
        )
        return redirect(url_for('bp_moderation.reports_index', report_id=report_id))

    form.process(data=dict(**report))
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
        report = await delete_report(report_id)
        if report:
            await fc.delete_post(report['board_shortname'], report['num'], report['op'])
        return redirect(url_for('bp_moderation.reports_index'))

    return await render_controller(
        template_reports_delete,
        report_id=report_id,
        title='Delete Report',
        tab_title='Delete Report',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )
