import quart_flask_patch

from collections import defaultdict
from html import escape

from flask_paginate import Pagination
from quart import Blueprint, flash, jsonify, redirect, request, url_for
from moderation.auth import login_web_usr_required

from asagi_converter import get_post
from boards import board_shortnames
from configs import mod_conf
from enums import ModStatus, PublicAccess
from forms import ReportUserForm
from leafs import (
    generate_post_html,
    post_files_hide,
)
from moderation.filter_cache import fc
from moderation.report import (
    create_report,
    get_report_count_all,
    get_report_count_f,
    get_reports_f,
    reports_action_routine
)
from moderation.user import Permissions
from moderation.auth import (
    require_web_usr_is_active,
    require_web_usr_permissions,
    load_web_usr_data,
)
from moderation.auth import current_web_usr
from render import render_controller
from templates import template_reports_index
from utils.validation import validate_board

bp = Blueprint('bp_web_moderation', __name__)


@bp.post('/report/<string:board_shortname>/<int:thread_num>/<int:num>')
async def create_report(board_shortname: str, thread_num: int, num: int):
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
            post = await get_post(board_shortname, num)
            post_files_hide(post)

        return jsonify({'message': 'thank you'})
    return jsonify({'message': f'error: {form.data}: {form.errors}'})


async def formulate_reports_for_html_table(reports: list[dict]) -> list[dict]:
    """We only want a subset of reporting columns, and we want them formatted."""
    ds = []
    for r in reports:
        d = {}

        report_parent_id = int(r.report_parent_id)

        d['Check'] = f'<input type="checkbox" class="select_report" data-report-id="{report_parent_id}">'

        endpoint = f"""<input type="hidden" name="endpoint" value="{request.endpoint}">"""
        d['About'] = f"""
        [<a href="/{r.board_shortname}/thread/{r.thread_num}#p{r.num}" rel="noreferrer" target="_blank">View</a>]
        [<a href="https://boards.4chan.org/{r.board_shortname}/thread/{r.thread_num}#p{r.num}" rel="noreferrer" target="_blank">Source</a>]
        <br>
        <br>
        [
            <form class="actionform" action="{url_for('bp_web_moderation.reports_action', report_parent_id=report_parent_id, action='post_hide')}"   method="post">{endpoint}<button {'disabled' if r.public_access == PublicAccess.hidden else ''} class="rbtn" type="submit">Post Hide</button></form> |
            <form class="actionform" action="{url_for('bp_web_moderation.reports_action', report_parent_id=report_parent_id, action='post_show')}"   method="post">{endpoint}<button {'disabled' if r.public_access == PublicAccess.visible else ''} class="rbtn" type="submit">Post Show</button></form> |
            <form class="actionform" action="{url_for('bp_web_moderation.reports_action', report_parent_id=report_parent_id, action='report_open')}"   method="post">{endpoint}<button {'disabled' if r.mod_status == ModStatus.open else ''} class="rbtn" type="submit">Report Open</button></form> |
            <form class="actionform" action="{url_for('bp_web_moderation.reports_action', report_parent_id=report_parent_id, action='report_close')}"  method="post">{endpoint}<button {'disabled' if r.mod_status == ModStatus.closed else ''} class="rbtn" type="submit">Report Close</button></form>
        ]
        <br>
        <br>
        <form class="actionform" action="{url_for('bp_web_moderation.reports_action', report_parent_id=report_parent_id, action='report_save_notes')}" method="post">
            <textarea name="mod_notes" rows="2" cols="20" placeholder="Moderation notes">{escape(r.mod_notes) if r.mod_notes else ''}</textarea>
            [<button class="rbtn" type="submit">Save Notes</button>]
        </form>
        <br>
        <br>
        <b>Count:</b> {int(r.report_count)}
        <br>
        <b>Category:</b> {escape(r.submitter_category)}
        <br>
        <b>Note:</b> {escape(r.submitter_notes)}
        """

        # ordering for populating the dict, d, matters, but I put these here to short circuit the loop if no post is found
        post_html = await generate_post_html(r.board_shortname, r.num)
        # if post_html.startswith('Error'):
        #     continue # likely deleted, but not removed from posts table due to it possibly being in FTS

        link = f'<a href="/{r.board_shortname}/thread/{r.thread_num}#p{r.num}">/{r.board_shortname}/thread/{r.thread_num}</a>'
        d['Post'] = post_html if post_html else link

        ds.append(d)
    return ds


def get_report_mod_status_link(mod_status: ModStatus) -> str:
    if mod_status == ModStatus.closed:
        return f'<a href="{url_for('bp_web_moderation.reports_open')}">Go to open reports</a>'
    return f'<a href="{url_for('bp_web_moderation.reports_closed')}">Go to closed reports</a>'


# should use **kwargs in the future
async def make_report_pagination(mod_status: ModStatus, board_shortnames: list[str], report_len: int, page_num: int, page_size: int=20):
    report_count_f = await get_report_count_f(mod_status=mod_status, board_shortnames=board_shortnames)
    report_count_all = await get_report_count_all()
    page_size = min(page_size, report_len)
    href=f'/reports/{mod_status.name}/' + '{0}'
    record_name = f'{mod_status.name} reports'

    pagination = Pagination(
        page=page_num,
        per_page=page_size,
        page_parameter=None,
        display_msg=f'Displaying <b>{page_size}</b> / <b>{report_count_f}</b> {mod_status.name} reports. <b>{report_count_all}</b> reports in total.',
        total=report_count_f,
        search=False,
        record_name=record_name,
        href=href,
        show_single_page=True,
    )
    return pagination


@bp.get('/reports/closed')
@bp.get('/reports/closed/<int:page_num>')
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.report_read])
async def reports_closed(page_num: int=0):
    page_size = 20
    reports = await get_reports_f(mod_status=ModStatus.closed, board_shortnames=board_shortnames, page_num=page_num, page_size=page_size)
    pagination = await make_report_pagination(ModStatus.closed, board_shortnames, len(reports), page_num, page_size=page_size)
    return await render_controller(
        template_reports_index,
        pagination=pagination,
        mod_status_link=get_report_mod_status_link(ModStatus.closed),
        reports=await formulate_reports_for_html_table(reports),
        title='Closed Reports',
        tab_title='Closed Reports',
        is_authenticated=True,
        is_admin=current_web_usr.is_admin,
    )


@bp.get('/reports/open')
@bp.get('/reports/open/<int:page_num>')
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.report_read])
async def reports_open(page_num: int=0):
    page_size=20
    reports = await get_reports_f(mod_status=ModStatus.open, board_shortnames=board_shortnames, page_num=page_num, page_size=page_size)
    pagination = await make_report_pagination(ModStatus.open, board_shortnames, len(reports), page_num, page_size=page_size)

    return await render_controller(
        template_reports_index,
        pagination=pagination,
        mod_status_link=get_report_mod_status_link(ModStatus.open),
        reports=await formulate_reports_for_html_table(reports),
        title='Reports',
        tab_title='Reports',
        is_authenticated=True,
        is_admin=current_web_usr.is_admin,
    )


@bp.route('/reports/<int:report_parent_id>/<string:action>', methods=['POST'])
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.report_read])
async def reports_action(report_parent_id: int, action: str):
    form = (await request.form)
    redirect_endpoint = form.get('endpoint', 'bp_moderation.reports_open')

    msg, code = await reports_action_routine(current_web_usr, report_parent_id, action, mod_notes=form.get('mod_notes'))
    if msg:
        await flash(msg)

    return redirect(url_for(redirect_endpoint))


@bp.route('/reports/bulk/<string:action>', methods=['POST'])
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.report_read])
async def reports_action_bulk(action: str):
    data = (await request.get_json())

    report_parent_ids = data.get('report_parent_ids', [])

    if not report_parent_ids:
        await flash('No reports submitted.')

    msgs = defaultdict(lambda: 0)
    for report_parent_id in report_parent_ids:
        msg, code = await reports_action_routine(current_web_usr, report_parent_id, action)
        msgs[msg] += 1

    if msgs:
        await flash('<br>'.join([f'{msg} x{n}' for msg, n in msgs.items()]))

    return jsonify({}), 200 # the client will reload itself
