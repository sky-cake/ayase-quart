from quart import Blueprint, abort, flash, jsonify, redirect, request, url_for

from configs import mod_conf
from enums import AuthActions, ModStatus, PublicAccess
from forms import ReportUserForm
from leafs import generate_post_html
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
from templates import template_reports_index
from utils.validation import validate_board
from html import escape

bp = Blueprint('bp_moderation', __name__)


@bp.route('/report/<string:board_shortname>/<int:thread_num>/<int:num>', methods=['POST'])
async def report(board_shortname: str, thread_num: int, num: int):
    form: ReportUserForm = await ReportUserForm.create_form(meta={'csrf': False})

    validate_board(board_shortname)

    if await form.validate_on_submit():
        submitter_category = form.submitter_category.data
        submitter_notes = form.submitter_notes.data

        op = thread_num == num
        await create_report(
            board_shortname,
            thread_num,
            num,
            op,
            request.remote_addr,
            submitter_notes,
            submitter_category,
            ModStatus.open,
            None,
        )
        if mod_conf['default_reported_post_public_access'] == PublicAccess.hidden:
            await fc.insert_post(board_shortname, num, op)

        return jsonify({'message': 'thank you'})
    return jsonify({'message': f'error: {form.data}: {form.errors}'})


async def formulate_reports_for_html_table(reports: list[dict]) -> list[dict]:
    """We only want a subset of reporting columns, and we want them formatted."""
    ds = []
    for r in reports:
        d = {}

        report_parent_id = int(r.report_parent_id)
        endpoint = f"""<input type="hidden" name="endpoint" value="{request.endpoint}">"""
        d['About'] = f"""
        [<a href="/g/thread/{r.thread_num}#p{r.num}" rel="noreferrer" target="_blank">View</a>]
        [<a href="https://boards.4chan.org/g/thread/{r.thread_num}#p{r.num}" rel="noreferrer" target="_blank">Source</a>]
        <br>
        <br>
        [
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='hide')}"   method="post">{endpoint}<button {'disabled' if r.public_access == PublicAccess.hidden else ''} class="rbtn" type="submit">Hide</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='show')}"   method="post">{endpoint}<button {'disabled' if r.public_access == PublicAccess.visible else ''} class="rbtn" type="submit">Show</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='open')}"   method="post">{endpoint}<button {'disabled' if r.mod_status == ModStatus.open else ''} class="rbtn" type="submit">Open</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='close')}"  method="post">{endpoint}<button {'disabled' if r.mod_status == ModStatus.closed else ''} class="rbtn" type="submit">Close</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='delete')}" method="post">{endpoint}<button class="rbtn" type="submit">Delete</button></form>
        ]
        <br>
        <br>
        <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='notes')}" method="post">
            <textarea name="mod_notes" rows="2" cols="20" placeholder="Moderation notes">{escape(r.mod_notes) if r.mod_notes else ''}</textarea>
            [<button class="rbtn" type="submit">Save</button>]
        </form>
        <br>
        <br>
        <b>Count:</b> {int(r.report_count)}
        <br>
        <b>Category:</b> {escape(r.submitter_category)}
        <br>
        <b>Note:</b> {escape(r.submitter_notes)}
        """

        post_html = await generate_post_html(r.board_shortname, r.num)
        link = f'<a href="/{r.board_shortname}/thread/{r.thread_num}#p{r.num}"> /{r.board_shortname}/thread/{r.thread_num} </a>'
        d['Post'] = post_html if post_html else link

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


@bp.route('/reports/<int:report_parent_id>/<string:action>', methods=['POST'])
@authorization_required
async def reports_action(report_parent_id: int, action: str):
    """Having this endpoint being POST-only is important."""

    report = await get_report_by_id(report_parent_id)
    if not report:
        abort(404)

    form = (await request.form)
    redirect_endpoint = form.get('endpoint', 'bp_moderation.reports_open')
    flash_msg = ''

    match action:
        case 'delete':
            report = await delete_report_if_exists(report_parent_id)
            flash_msg = 'Report was already deleted.'
            if report:
                await fc.delete_post(report['board_shortname'], report['num'], report['op'])
                flash_msg = 'Report deleted.'

        case 'show':
            report = await edit_report_if_exists(report_parent_id, public_access=PublicAccess.visible)
            await fc.delete_post(report['board_shortname'], report['num'], report['op'])
            flash_msg = 'Post now publicly visible.'

        case 'hide':
            report = await edit_report_if_exists(report_parent_id, public_access=PublicAccess.hidden)
            if report:
                await fc.insert_post(report['board_shortname'], report['num'], report['op'])
    
            flash_msg = 'Post now publicly hidden.'

        case 'close':
            report = await edit_report_if_exists(report_parent_id, mod_status=ModStatus.closed)
            flash_msg = 'Report moved to closed reports.'

        case 'open':
            report = await edit_report_if_exists(report_parent_id, mod_status=ModStatus.open)
            flash_msg = 'Report moved to opened reports.'

        case 'notes':
            mod_notes = form.get('mod_notes')
            await edit_report_if_exists(report_parent_id, mod_notes=mod_notes)
            flash_msg = 'Saved moderation notes.'

        case _:
            abort(404)

    if flash_msg:
        await flash(flash_msg)

    return redirect(url_for(redirect_endpoint))
