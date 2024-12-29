from collections import defaultdict
from html import escape

from quart import Blueprint, abort, flash, jsonify, redirect, request, url_for

from asagi_converter import get_post, move_post_to_delete_table
from boards import board_shortnames
from configs import mod_conf
from enums import AuthActions, ModStatus, PublicAccess
from forms import ReportUserForm
from leafs import (
    delete_file_if_shown_or_hidden,
    generate_post_html,
    hide_file_if_shown,
    show_file_if_hidden
)
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

        d['Check'] = f'<input type="checkbox" class="select_report" data-report-id="{report_parent_id}">'

        endpoint = f"""<input type="hidden" name="endpoint" value="{request.endpoint}">"""
        d['About'] = f"""
        [<a href="/{r.board_shortname}/thread/{r.thread_num}#p{r.num}" rel="noreferrer" target="_blank">View</a>]
        [<a href="https://boards.4chan.org/{r.board_shortname}/thread/{r.thread_num}#p{r.num}" rel="noreferrer" target="_blank">Source</a>]
        <br>
        <br>
        [
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='post_hide')}"   method="post">{endpoint}<button {'disabled' if r.public_access == PublicAccess.hidden else ''} class="rbtn" type="submit">Post Hide</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='post_show')}"   method="post">{endpoint}<button {'disabled' if r.public_access == PublicAccess.visible else ''} class="rbtn" type="submit">Post Show</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='report_open')}"   method="post">{endpoint}<button {'disabled' if r.mod_status == ModStatus.open else ''} class="rbtn" type="submit">Report Open</button></form> |
            <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='report_close')}"  method="post">{endpoint}<button {'disabled' if r.mod_status == ModStatus.closed else ''} class="rbtn" type="submit">Report Close</button></form>
        ]
        <br>
        <br>
        <form class="actionform" action="{url_for('bp_moderation.reports_action', report_parent_id=report_parent_id, action='report_save_notes')}" method="post">
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
        return f'<a href="{url_for('bp_moderation.reports_open')}">Go to open reports</a>'
    return f'<a href="{url_for('bp_moderation.reports_closed')}">Go to closed reports</a>'


@bp.route('/reports/closed')
@authorization_required
async def reports_closed():
    reports = await get_all_reports(mod_status=ModStatus.closed, board_shortnames=board_shortnames)

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
    reports = await get_all_reports(mod_status=ModStatus.open, board_shortnames=board_shortnames)

    return await render_controller(
        template_reports_index,
        mod_status_link=get_report_mod_status_link(ModStatus.open),
        reports=await formulate_reports_for_html_table(reports),
        title='Reports',
        tab_title='Reports',
        is_logged_in=True,
        is_admin=await auth(AuthActions.is_admin),
    )


async def reports_action_routine(report_parent_id: int, action: str, mod_notes: str=None) -> str:
    # must be POST to avoid duplicating actions on historic page-visits
    if request.method != 'POST':
        abort(400)

    report = await get_report_by_id(report_parent_id)
    if not report:
        return f'Could not find report with id {report_parent_id}.'

    flash_msg = ''

    match action:
        case 'report_delete':
            report = await delete_report_if_exists(report_parent_id)
            flash_msg = f'Report was already deleted.'
            if report:
                await fc.delete_post(report['board_shortname'], report['num'], report['op'])
                flash_msg = f'Report deleted.'
            return flash_msg

        case 'post_delete':
            # Note: do not delete the report here. It is still needed to filter outgoing posts from full text search.
            post, result = await move_post_to_delete_table(report.board_shortname, report.num)
            if result == 0:
                flash_msg = 'Did not locate post in asagi database. Did nothing as a result.'
            elif result == -1:
                flash_msg = 'Did not transfer post to asagi\'s delete table. It is still in the board table.'
            elif result == 1:
                flash_msg = 'Post transfered to asagi\'s delete table. It is no longer in the board table.'
            else:
                raise ValueError(post, result)

            r = delete_file_if_shown_or_hidden(report.board_shortname, post.get('media_orig'), False)
            flash_msg += ' Deleted full media.' if r else ' Did not delete full media.'
            r = delete_file_if_shown_or_hidden(report.board_shortname, post.get("preview_orig"), True)
            flash_msg += ' Deleted thumbnail.' if r else ' Did not delete thumbnail.'

        case 'media_delete':
            post = await get_post(report.board_shortname, report.num)
            r = delete_file_if_shown_or_hidden(report.board_shortname, post.get('media_orig'), False)
            flash_msg += ' Deleted full media.' if r else ' Did not delete full media.'
            r = delete_file_if_shown_or_hidden(report.board_shortname, post.get("preview_orig"), True)
            flash_msg += ' Deleted thumbnail.' if r else ' Did not delete thumbnail.'

        case 'media_hide':
            post = await get_post(report.board_shortname, report.num)
            r = hide_file_if_shown(report.board_shortname, post.get('media_orig'), False)
            flash_msg += ' Hid full media.' if r else ' Did not hide full media.'
            r = hide_file_if_shown(report.board_shortname, post.get('preview_orig'), True)
            flash_msg += ' Hid thumbnail.' if r else ' Did not hide thumbnail.'

        case 'media_show':
            post = await get_post(report.board_shortname, report.num)
            r = show_file_if_hidden(report.board_shortname, post.get('media_orig'), False)
            flash_msg += ' Showing full media.' if r else ' Did not reveal full media.'
            r = show_file_if_hidden(report.board_shortname, post.get('preview_orig'), True)
            flash_msg += ' Showing thumbnail.' if r else ' Did not reveal thumbnail.'

        case 'post_show':
            report = await edit_report_if_exists(report_parent_id, public_access=PublicAccess.visible)
            await fc.delete_post(report['board_shortname'], report['num'], report['op'])
            flash_msg = f'Post now publicly visible.'
    
            hidden_images_path = mod_conf.get('hidden_images_path')
            if hidden_images_path:
                post = await get_post(report.board_shortname, report.num)

                show_file_if_hidden(report.board_shortname, post.get('media_orig'), True)
                show_file_if_hidden(report.board_shortname, post.get('preview_orig'), False)

        case 'post_hide':
            report = await edit_report_if_exists(report_parent_id, public_access=PublicAccess.hidden)
            if report:
                await fc.insert_post(report['board_shortname'], report['num'], report['op'])

            hidden_images_path = mod_conf.get('hidden_images_path')
            if hidden_images_path:
                post = await get_post(report.board_shortname, report.num)

                hide_file_if_shown(report.board_shortname, post.get('media_orig'), True)
                hide_file_if_shown(report.board_shortname, post.get('preview_orig'), False)
    
            flash_msg = 'Post now publicly hidden.'

        case 'report_close':
            report = await edit_report_if_exists(report_parent_id, mod_status=ModStatus.closed)
            flash_msg = 'Report moved to closed reports.'

        case 'report_open':
            report = await edit_report_if_exists(report_parent_id, mod_status=ModStatus.open)
            flash_msg = 'Report moved to opened reports.'

        case 'report_save_notes':
            # falsey mod_notes are valid
            await edit_report_if_exists(report_parent_id, mod_notes=mod_notes)
            flash_msg = f'Report had their moderation notes saved.'

        case _:
            abort(404)

    return flash_msg


@bp.route('/reports/<int:report_parent_id>/<string:action>', methods=['POST'])
@authorization_required
async def reports_action(report_parent_id: int, action: str):
    form = (await request.form)
    redirect_endpoint = form.get('endpoint', 'bp_moderation.reports_open')

    msg = await reports_action_routine(report_parent_id, action, mod_notes=form.get('mod_notes'))
    if msg:
        await flash(msg)

    return redirect(url_for(redirect_endpoint))


@bp.route('/reports/bulk/<string:action>', methods=['POST'])
@authorization_required
async def reports_action_bulk(action: str):
    data = (await request.get_json())

    report_parent_ids = data.get('report_parent_ids', [])

    if not report_parent_ids:
        await flash('No reports submitted.')

    msgs = defaultdict(lambda: 0)
    for report_parent_id in report_parent_ids:
        msg = await reports_action_routine(report_parent_id, action)
        msgs[msg] += 1

    if msgs:
        await flash('<br>'.join([f'{msg} x{n}' for msg, n in msgs.items()]))

    return jsonify({}), 200 # the client will reload itself
