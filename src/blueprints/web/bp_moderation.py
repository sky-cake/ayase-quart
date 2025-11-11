from collections import defaultdict
from datetime import timedelta
from html import escape

from quart import Blueprint, flash, jsonify, redirect, request, url_for
from quart_rate_limiter import rate_limit

from asagi_converter import get_post
from boards import board_shortnames
from configs import archiveposting_conf, mod_conf
from db import db_a, db_q
from enums import ModStatus, PublicAccess
from forms import ReportUserForm
from leafs import generate_post_html, post_files_hide
from moderation import fc
from moderation.auth import (
    current_web_usr,
    load_web_usr_data,
    login_web_usr_required,
    require_web_usr_is_active,
    require_web_usr_permissions,
    web_usr_is_admin
)
from moderation.report import (
    create_report,
    get_report_count,
    get_reports,
    reports_action_routine
)
from moderation.user import Permissions
from paginate import Pagination
from render import render_controller
from templates import template_reports_index
from utils.validation import validate_board
from security import apply_csrf_validation_on_endpoint, session_csrf_token_name, validate_csrf_token, get_csrf_input


bp = Blueprint('bp_web_moderation', __name__)


@bp.post('/report/<string:board>/<int:thread_num>/<int:num>')
@apply_csrf_validation_on_endpoint
@rate_limit(4, timedelta(hours=1))
async def route_create_report(board: str, thread_num: int, num: int):

    # turn csrf on the form, and use route decorator to validate csrf on api requests
    form: ReportUserForm = await ReportUserForm.create_form(meta={'csrf': False})

    if board != archiveposting_conf['board_name']:
        validate_board(board)
        db_X = db_q
    elif board == archiveposting_conf['board_name']:
        db_X = db_a
    else:
        raise ValueError()

    if request.method == 'POST' and (await form.validate_on_submit()):
        submitter_category = form.submitter_category.data
        submitter_notes = form.submitter_notes.data
        
        post = await get_post(board, num, db_X=db_X)
        if not post:
            return jsonify({'message': 'we dont have this post archived'})

        op = thread_num == num
        await create_report(
            board,
            thread_num,
            num,
            op,
            request.remote_addr,
            submitter_notes,
            submitter_category,
            ModStatus.open,
            None,
        )

        if mod_conf['hide_post_if_reported']:
            post_files_hide(post)
            await fc.insert_post(board, num, op)

        elif mod_conf['n_reports_then_hide'] > 0:
            report_strikes = await get_report_count(board_shortnames=[board], num=num, number_of_reported_posts_only=False)
            if report_strikes > mod_conf['n_reports_then_hide']:
                post_files_hide(post)
                await fc.insert_post(board, num, op)    

        return jsonify({'message': 'thank you'})
    return jsonify({'message': f'error: {form.data}: {form.errors}'})


async def formulate_reports_for_html_table(reports: list[dict]) -> list[dict]:
    """We only want a subset of reporting columns, and we want them formatted."""
    ds = []
    csrf_input = get_csrf_input()
    for r in reports:
        d = {}

        report_parent_id = int(r.report_parent_id)

        d['Check'] = f'<input type="checkbox" class="select_report" data-report-id="{report_parent_id}">'

        source_link = ''
        if archiveposting_conf['enabled'] and archiveposting_conf['board_name'] != r.board_shortname:
            source_link = f'[<a href="https://boards.4chan.org/{r.board_shortname}/thread/{r.thread_num}#p{r.num}" rel="noreferrer" target="_blank">Source</a>]'

        endpoint_html = f"""<input type="hidden" name="endpoint" value="{request.endpoint}">"""
        d['About'] = f"""
        [<a href="/{r.board_shortname}/thread/{r.thread_num}#p{r.num}" rel="noreferrer" target="_blank">View</a>] {source_link}
        <br>
        <br>
        [
            <form class="actionform form" action="{url_for('bp_web_moderation.reports_action', report_parent_id=report_parent_id, action='post_hide')}"     method="post">{csrf_input}{endpoint_html}<button {'disabled' if r.public_access == PublicAccess.hidden else ''} class="rbtn" type="submit">Post Hide</button></form> |
            <form class="actionform form" action="{url_for('bp_web_moderation.reports_action', report_parent_id=report_parent_id, action='post_show')}"     method="post">{csrf_input}{endpoint_html}<button {'disabled' if r.public_access == PublicAccess.visible else ''} class="rbtn" type="submit">Post Show</button></form> |
            <form class="actionform form" action="{url_for('bp_web_moderation.reports_action', report_parent_id=report_parent_id, action='report_open')}"   method="post">{csrf_input}{endpoint_html}<button {'disabled' if r.mod_status == ModStatus.open else ''} class="rbtn" type="submit">Report Open</button></form> |
            <form class="actionform form" action="{url_for('bp_web_moderation.reports_action', report_parent_id=report_parent_id, action='report_close')}"  method="post">{csrf_input}{endpoint_html}<button {'disabled' if r.mod_status == ModStatus.closed else ''} class="rbtn" type="submit">Report Close</button></form>
        ]
        <br>
        <br>
        <form class="actionform form" action="{url_for('bp_web_moderation.reports_action', report_parent_id=report_parent_id, action='report_save_notes')}" method="post">
            {csrf_input}
            <textarea name="mod_notes" rows="2" cols="20" placeholder="Moderation notes">{escape(r.mod_notes) if r.mod_notes else ''}</textarea>
            [<button class="rbtn" type="submit">Save Notes</button>]
        </form>
        <br>
        <br>
        <b>IP Count:</b> {int(r.ip_count)}
        <br>
        <b>Category:</b> {escape(r.submitter_category)}
        <br>
        <b>Note:</b> {escape(r.submitter_notes)}
        """

        db_X = db_q
        if archiveposting_conf['enabled'] and r.board_shortname == archiveposting_conf['board_name']:
            db_X = db_a

        # ordering for populating the dict, d, matters, but I put these here to short circuit the loop if no post is found
        post_html = await generate_post_html(r.board_shortname, r.num, db_X=db_X)
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
async def make_report_pagination(mod_status: ModStatus, boards: list[str], report_len: int, page_num: int, page_size: int=20):

    bs = boards + [archiveposting_conf['board_name']] if archiveposting_conf['enabled'] else boards

    report_count = await get_report_count(mod_status=mod_status, board_shortnames=bs)
    report_count_all = await get_report_count()
    page_size = min(page_size, report_len)
    href=f'/reports/{mod_status.name}/' + '{0}'
    record_name = f'{mod_status.name} reports'

    pagination = Pagination(
        page=page_num,
        per_page=page_size,
        page_parameter=None,
        display_msg=f'Displaying <b>{page_size}</b> / <b>{report_count}</b> {mod_status.name} reports. <b>{report_count_all}</b> reports in total.',
        total=report_count,
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
@web_usr_is_admin
async def reports_closed(is_admin: bool, page_num: int=0):
    page_size = 20
    bs = board_shortnames + [archiveposting_conf['board_name']] if archiveposting_conf['enabled'] else board_shortnames
    reports = await get_reports(mod_status=ModStatus.closed, board_shortnames=bs, page_num=page_num, page_size=page_size)
    pagination = await make_report_pagination(ModStatus.closed, bs, len(reports), page_num, page_size=page_size)
    return await render_controller(
        template_reports_index,
        pagination=pagination,
        mod_status_link=get_report_mod_status_link(ModStatus.closed),
        reports=await formulate_reports_for_html_table(reports),
        title='Closed Reports',
        tab_title='Closed Reports',
        logged_in=True,
        is_admin=is_admin,
        csrf_input=get_csrf_input(),
    )


@bp.get('/reports/open')
@bp.get('/reports/open/<int:page_num>')
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.report_read])
@web_usr_is_admin
async def reports_open(is_admin: bool, page_num: int=0):
    page_size=20
    bs = board_shortnames + [archiveposting_conf['board_name']] if archiveposting_conf['enabled'] else board_shortnames
    reports = await get_reports(mod_status=ModStatus.open, board_shortnames=bs, page_num=page_num, page_size=page_size)
    pagination = await make_report_pagination(ModStatus.open, bs, len(reports), page_num, page_size=page_size)

    return await render_controller(
        template_reports_index,
        pagination=pagination,
        mod_status_link=get_report_mod_status_link(ModStatus.open),
        reports=await formulate_reports_for_html_table(reports),
        title='Reports',
        tab_title='Reports',
        logged_in=True,
        is_admin=is_admin,
        csrf_input=get_csrf_input(),
    )


@bp.post('/reports/<int:report_parent_id>/<string:action>')
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.report_read])
async def reports_action(report_parent_id: int, action: str):
    form = (await request.form)

    # csrf added as hidden input field in bp.get() route
    token = form.get(session_csrf_token_name)
    validate_csrf_token(token)

    redirect_endpoint = form.get('endpoint', 'bp_web_moderation.reports_open')

    msg, code = await reports_action_routine(current_web_usr, report_parent_id, action, mod_notes=form.get('mod_notes'))
    if msg:
        await flash(msg)

    return redirect(url_for(redirect_endpoint))


@bp.post('/reports/bulk/<string:action>')
@login_web_usr_required
@load_web_usr_data
@require_web_usr_is_active
@require_web_usr_permissions([Permissions.report_read])
async def reports_action_bulk(action: str):
    data: dict = await request.get_json()

    # csrf added as hidden input field in bp.get() route
    token = data.get(session_csrf_token_name)
    validate_csrf_token(token)

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
