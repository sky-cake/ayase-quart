from datetime import datetime
from typing import Optional

from moderation.user import Permissions

from asagi_converter import get_post, move_post_to_delete_table, get_local_db_q
from configs import mod_conf, archiveposting_conf, index_search_conf
from db import db_m, db_a, db_q
from enums import DbPool, ModStatus, PublicAccess, SubmitterCategory, ReportAction
from leafs import post_files_delete, post_files_hide, post_files_show
from moderation import fc
from moderation.user import User
from utils.validation import validate_board
from search.providers import get_index_search_provider
from search.post_metadata import board_2_int, board_int_doc_id_2_pk


# this can actually just be a jinja form that is compiled once...
def generate_report_modal():
    category_options = "\n".join(
        f"""
        <div>
          <input type="radio" id="{category.name}" name="submitter_category" value="{category.value}" required>
          <label for="{category.name}">{category.value}</label>
        </div>
        """ for category in SubmitterCategory
    )
    modal_html = f"""
    <div id="modal_overlay" hidden>
        <div id="report_modal" class="form" hidden>
            <div class="modal_header">
                <div class="modal_title">Report</div>
                <div id="report_close" class="btn">Close</div>
            </div>
            <form class="form" id="report_form" action="" method="POST">
                <div>
                    <label for="submitter_category">Category:</label>
                    {category_options}
                </div>
                <br>
                <div>
                    <label for="submitter_notes">Details:</label>
                    <textarea id="submitter_notes" name="submitter_notes" cols="48" rows="8" maxlength="512" placeholder="Provide details about the issue."></textarea>
                </div>
                <br>
                <div id="feedback_report"></div>
                <input type="submit" value="Submit" class="mb05">
            </form>
        </div>
    </div>
    """
    return modal_html

report_modal_t = generate_report_modal()

async def get_report_count(
    report_parent_id: Optional[int] = None,
    board_shortnames: Optional[list[str]] = None,
    thread_num: Optional[int] = None,
    num: Optional[int] = None,
    is_op: Optional[bool] = None,
    public_access: Optional[PublicAccess] = None,
    mod_status: Optional[ModStatus] = None,
    submitter_category: Optional[SubmitterCategory] = None,
    created_at_gte: Optional[str] = None,
    created_at_lte: Optional[str] = None,
    number_of_reported_posts_only: bool=True,
    **kwargs,
) -> int:
    """
    - `number_of_reported_posts_only` True -> the number of reported posts.
    - `number_of_reported_posts_only` False -> the number of reports.
    - `kwargs` is just a convenience here, it gobbles up any extra, unused params for us.
    """
    ph = db_m.phg()
    where = []
    params = []

    if public_access:
        where.append(f'public_access = {ph}')
        params.append(public_access)
    if mod_status:
        where.append(f'mod_status = {ph}')
        params.append(mod_status)
    if board_shortnames:
        assert isinstance(board_shortnames, list)
        assert isinstance(board_shortnames[0], str)
        where.append(f'board_shortname in ({db_m.phg.qty(len(board_shortnames))})')
        params.extend(board_shortnames)
    if report_parent_id:
        where.append(f'report_parent_id = {ph}')
        params.append(report_parent_id)
    if num:
        where.append(f'num = {ph}')
        params.append(num)
    if thread_num:
        where.append(f'thread_num = {ph}')
        params.append(thread_num)
    if is_op:
        where.append('op = 1')
    if is_op is not None and not is_op:
        where.append('op != 1')

    where_child = []
    if submitter_category:
        where_child.append(f'submitter_category = {ph}')
        params.append(submitter_category)
    if created_at_gte:
        where_child.append(f'created_at >= {ph}')
        params.append(created_at_gte)
    if created_at_lte:
        where_child.append(f'created_at =< {ph}')
        params.append(created_at_lte)

    sql_join = ''
    if not number_of_reported_posts_only:
        # get number of reports, not just reported post count
        sql_join = 'join report_child using (report_parent_id)'

    sql = f"""
        select
            count(*) as report_count
        from report_parent
            {sql_join}
    """
    if where:
        sql += ' where ' + ' and '.join(where)

    if where_child:
        w = ' and '.join(where_child)
        sql += f' and report_parent_id in ( select report_parent_id from report_child where {w})'

    if (reports := (await db_m.query_dict(sql, params=params, p_id=DbPool.mod))):
        return reports[0]['report_count']
    return 0


async def get_reports(
    report_parent_id: Optional[int] = None,
    board_shortnames: Optional[list[str]] = None,
    thread_num: Optional[int] = None,
    num: Optional[int] = None,
    is_op: Optional[bool] = None,
    public_access: Optional[PublicAccess] = None,
    mod_status: Optional[ModStatus] = None,
    submitter_category: Optional[SubmitterCategory] = None,
    created_at_gte: Optional[str] = None,
    created_at_lte: Optional[str] = None,
    page_num: int = 0,
    page_size: int = 20
) -> Optional[list[dict]] | int:

    ph = db_m.phg()
    where = []
    params = []

    if public_access:
        where.append(f'rp.public_access = {ph}')
        params.append(public_access)
    if mod_status:
        where.append(f'rp.mod_status = {ph}')
        params.append(mod_status)
    if board_shortnames:
        assert isinstance(board_shortnames, list)
        assert isinstance(board_shortnames[0], str)
        where.append(f'rp.board_shortname in ({db_m.phg.qty(len(board_shortnames))})')
        params.extend(board_shortnames)
    if report_parent_id:
        where.append(f'rp.report_parent_id = {ph}')
        params.append(report_parent_id)
    if num:
        where.append(f'rp.num = {ph}')
        params.append(num)
    if submitter_category:
        where.append(f'rc.submitter_category = {ph}')
        params.append(submitter_category)
    if thread_num:
        where.append(f'rp.thread_num = {ph}')
        params.append(thread_num)
    if is_op:
        where.append('rp.op = 1')
    if is_op is not None and not is_op:
        where.append('rp.op != 1')
    if created_at_gte:
        where.append(f'rc.created_at >= {ph}')
        params.append(created_at_gte)
    if created_at_lte:
        where.append(f'rc.created_at =< {ph}')
        params.append(created_at_lte)

    sql = """
        select
            rp.report_parent_id,
            rp.board_shortname,
            rp.num,
            rp.thread_num,
            rp.public_access,
            rp.mod_status,
            rp.mod_notes,
            count(distinct submitter_ip) as ip_count,
            group_concat(rc.submitter_category, '||') as submitter_category,
            group_concat(rc.submitter_notes, '||') as submitter_notes
        from report_parent rp
            join report_child rc using (report_parent_id)
    """
    if where:
        sql += ' where ' + ' and '.join(where)

    sql += f"""
        group by 1,2,3,4,5,6,7
        order by rc.report_parent_id, max(rc.created_at) desc
        limit {ph} offset {ph}
    """
    params.extend([page_size, page_num * page_size])

    if (reports := await db_m.query_dict(sql, params=params, p_id=DbPool.mod)):
        return reports
    return []


async def get_report_by_id(report_parent_id: int) -> Optional[dict]:
    if (reports := await db_m.query_dict(f'select * from report_parent where report_parent_id={db_m.phg()};', params=(report_parent_id,), p_id=DbPool.mod)):
        return reports[0]


async def get_report_by_board(board: str) -> Optional[list[dict]]:
    if (reports := await db_m.query_dict(f'select * from report_parent where board_shortname={db_m.phg()};', params=(board,), p_id=DbPool.mod)):
        return reports


async def get_report_by_post_num(board: str, num: int) -> Optional[list[dict]]:
    if (reports := await db_m.query_dict(f'select * from report_parent where board_shortname={db_m.phg()} and num={db_m.phg()};', params=(board, num,), p_id=DbPool.mod)):
        return reports


async def get_report_parent_id(board: str, num: int) -> Optional[int]:
    report_parent_id = None
    ph = db_m.phg()
    sql = f'select report_parent_id from report_parent where board_shortname = {ph} and num = {ph};'
    rows = await db_m.query_dict(sql, params=[board, num], p_id=DbPool.mod)
    if rows:
        report_parent_id = rows[0]['report_parent_id']
    return report_parent_id


async def create_report(
    board: str,
    thread_num: int,
    num: int,
    op: int,
    submitter_ip: str,
    submitter_notes: str,
    submitter_category: str,
    mod_status: str,
    mod_notes: str = None
):
    now = datetime.now()
    public_access = PublicAccess.hidden if mod_conf['hide_post_if_reported'] else PublicAccess.visible

    report_parent_id = await get_report_parent_id(board, num)

    if not report_parent_id:
        params_parent = [board, num, thread_num, op, mod_status, public_access, mod_notes, now]
        sql = f"""
            insert into
            report_parent (board_shortname, num, thread_num, op, mod_status, public_access, mod_notes, last_updated_at)
            values ({db_m.phg.size(params_parent)}) returning report_parent_id
        ;"""
        report_parent_id = (await db_m.query_dict(sql, params=params_parent, commit=True, p_id=DbPool.mod))[0]['report_parent_id']
        if not report_parent_id:
            raise ValueError(report_parent_id)

    params_child = [report_parent_id, submitter_ip, submitter_notes, submitter_category, now]
    sql = f"""
        insert or ignore into
            report_child (report_parent_id, submitter_ip, submitter_notes, submitter_category, created_at)
        values ({db_m.phg.size(params_child)})
    ;"""
    await db_m.query_dict(sql, params=params_child, commit=True, p_id=DbPool.mod)


async def edit_report_if_exists(report_parent_id: int, public_access: PublicAccess=None, mod_status: ModStatus=None, mod_notes: str=None) -> dict:
    if not (report := await get_report_by_id(report_parent_id)):
        return {}

    s = ''
    params = []

    if public_access:
        s += f' public_access={db_m.phg()}, '
        params.append(public_access.value)
    if mod_status:
        s += f' mod_status={db_m.phg()}, '
        params.append(mod_status.value)
    if mod_notes is not None:
        s += f' mod_notes={db_m.phg()}, '
        params.append(mod_notes)

    if not s:
        return

    sql = f"""
        update report_parent
        set {s} last_updated_at={db_m.phg()}
        where report_parent_id={db_m.phg()}
    ;"""
    params = params + [datetime.now(), report_parent_id]
    await db_m.query_dict(sql, params=params, commit=True, p_id=DbPool.mod)
    return report


async def delete_report_if_exists(report_parent_id: int) -> dict:
    if not (report := await get_report_by_id(report_parent_id)):
        return {}

    # cascading will delete `report_child` records
    sql = f'delete from report_parent where report_parent_id={db_m.phg()};'
    await db_m.query_dict(sql, params=(report_parent_id,), commit=True, p_id=DbPool.mod)

    return report


async def delete_post_from_index_if_applicable(bs: str, post: dict, remove_entire_thread_if_post_is_op: bool=False) -> bool:
    if not index_search_conf['enabled']:
        return False

    validate_board(bs)

    index_searcher = get_index_search_provider()
    board_int = board_2_int(bs)

    if remove_entire_thread_if_post_is_op and post['op']:
        rows = await db_q.query_dict(f"""select doc_id from `{bs}` where thread_num = {db_q.phg()}""", params=(post['num'],))
    else:
        rows = await db_q.query_dict(f"""select doc_id from `{bs}` where num = {db_q.phg()}""", params=(post['num'],))

    pk_ids = [board_int_doc_id_2_pk(board_int, row['doc_id']) for row in rows]
    if not pk_ids:
        return False

    await index_searcher.remove_posts(pk_ids)
    return True


async def reports_action_routine(current_usr: User, report_parent_id: int, action: str, mod_notes: str=None) -> tuple[str, int]:

    report = await get_report_by_id(report_parent_id)
    if not report:
        return f'Could not find report with id {report_parent_id}.', 404

    flash_msg = ''

    bs = report.board_shortname

    if bs != archiveposting_conf['board_name']:
        validate_board(bs)
        db_X = db_q
    elif archiveposting_conf['enabled'] and bs == archiveposting_conf['board_name']:
        db_X = db_a
    else:
        return f'Unknown board {bs}', 404

    match action:
        case ReportAction.report_delete:
            if not current_usr.has_permissions([Permissions.report_delete]):
                return f'Need permissions for {Permissions.report_delete.name}', 401

            report = await delete_report_if_exists(report_parent_id)
            flash_msg = 'Report seems to already be deleted.'
            if report:
                await fc.delete_post(report['board_shortname'], report['num'], report['op'])
                flash_msg = 'Report deleted.'

        case ReportAction.post_delete:
            if not current_usr.has_permissions([Permissions.post_delete]):
                return f'Need permissions for {Permissions.post_delete.name}', 401

            flash_msg = ''

            local_db_q = get_local_db_q(report.board_shortname)
            post = await get_post(report.board_shortname, report.num, db_X=local_db_q)
            if not post:
                # This block shouldn't be executed much, if at all.
                # We delete the post from the index, THEN delete the post from the database.
                # If we get here, there are other forces at play which are deleting post from the asagi database.
                flash_msg += ' Did not find post in asagi database.'

                # could implement this here to double check the post is not in the index
                # https://docs.lnx.rs/#tag/Managing-documents/operation/Delete_Documents_By_Query_indexes__index__documents_query_delete

                return flash_msg, 200

            # must come before deleting post from <board> table
            if (await delete_post_from_index_if_applicable(bs, post)):
                flash_msg += ' Deleted post from index.'

            # Old Note: do not delete the report here. It is still needed to filter outgoing posts from full text search.
            flash_msg += (await move_post_to_delete_table(post))

            full_del, prev_del = post_files_delete(post)
            flash_msg += ' Deleted full media.' if full_del else ' Did not delete full media.'
            flash_msg += ' Deleted thumbnail.' if prev_del else ' Did not delete thumbnail.'

            # delete report cus the post no longer exists, otherwise a bunch of empty reports will accumulate
            report = await delete_report_if_exists(report_parent_id)
            if report:
                await fc.delete_post(report['board_shortname'], report['num'], report['op'])
                flash_msg += ' Report deleted.'
            else:
                flash_msg += ' Report seems to already be deleted.'

        case ReportAction.media_delete:
            if not current_usr.has_permissions([Permissions.media_delete]):
                return f'Need permissions for {Permissions.media_delete.name}', 401

            post = await get_post(report.board_shortname, report.num, db_X=db_X)
            if not post:
                return 'Could not find post.', 404
            full_del, prev_del = post_files_delete(post)
            flash_msg += ' Deleted full media.' if full_del else ' Did not delete full media.'
            flash_msg += ' Deleted thumbnail.' if prev_del else ' Did not delete thumbnail.'

        case ReportAction.media_hide:
            if not current_usr.has_permissions([Permissions.media_hide]):
                return f'Need permissions for {Permissions.media_hide.name}', 401

            post = await get_post(report.board_shortname, report.num, db_X=db_X)
            if not post:
                return 'Could not find post.', 404
            full_hid, prev_hid = post_files_hide(post)
            flash_msg += ' Hid full media.' if full_hid else ' Did not hide full media.'
            flash_msg += ' Hid thumbnail.' if prev_hid else ' Did not hide thumbnail.'

        case ReportAction.media_show:
            if not current_usr.has_permissions([Permissions.media_show]):
                return f'Need permissions for {Permissions.media_show.name}', 401

            post = await get_post(report.board_shortname, report.num, db_X=db_X)
            if not post:
                return 'Could not find post.', 404
            full_sho, prev_sho = post_files_show(post)
            flash_msg += ' Showing full media.' if full_sho else ' Did not reveal full media.'
            flash_msg += ' Showing thumbnail.' if prev_sho else ' Did not reveal thumbnail.'

        case ReportAction.post_show:
            if not current_usr.has_permissions([Permissions.post_show]):
                return f'Need permissions for {Permissions.post_show.name}', 401

            report = await edit_report_if_exists(report_parent_id, public_access=PublicAccess.visible)
            if report:
                await fc.delete_post(report['board_shortname'], report['num'], report['op'])
            flash_msg = 'Post now publicly visible.'

            if mod_conf.get('hidden_images_path'):
                post = await get_post(report.board_shortname, report.num, db_X=db_X)
                if not post:
                    return 'Could not find post.', 404
                full_sho, prev_sho = post_files_show(post)
                flash_msg += ' Showing full media.' if full_sho else ' Did not reveal full media.'
                flash_msg += ' Showing thumbnail.' if prev_sho else ' Did not reveal thumbnail.'

        case ReportAction.post_hide:
            if not current_usr.has_permissions([Permissions.post_hide]):
                return f'Need permissions for {Permissions.post_hide.name}', 401

            report = await edit_report_if_exists(report_parent_id, public_access=PublicAccess.hidden)
            if report:
                await fc.insert_post(report['board_shortname'], report['num'], report['op'])
            flash_msg = 'Post now publicly hidden.'

            if mod_conf.get('hidden_images_path'):
                post = await get_post(report.board_shortname, report.num, db_X=db_X)
                if not post:
                    return 'Could not find post.', 404
                full_hid, prev_hid = post_files_hide(post)
                flash_msg += ' Hid full media.' if full_hid else ' Did not hide full media.'
                flash_msg += ' Hid thumbnail.' if prev_hid else ' Did not hide thumbnail.'

        case ReportAction.report_close:
            if not current_usr.has_permissions([Permissions.report_close]):
                return f'Need permissions for {Permissions.report_close.name}', 401

            report = await edit_report_if_exists(report_parent_id, mod_status=ModStatus.closed)
            flash_msg = 'Report moved to closed reports.'

        case ReportAction.report_open:
            if not current_usr.has_permissions([Permissions.report_open]):
                return f'Need permissions for {Permissions.report_open.name}', 401

            report = await edit_report_if_exists(report_parent_id, mod_status=ModStatus.open)
            flash_msg = 'Report moved to opened reports.'

        case ReportAction.report_save_notes:
            if not current_usr.has_permissions([Permissions.report_save_notes]):
                return f'Need permissions for {Permissions.report_save_notes.name}', 401

            # falsey mod_notes are valid
            await edit_report_if_exists(report_parent_id, mod_notes=mod_notes)
            flash_msg = 'Report had their moderation notes saved.'

        case _:
            return 'Unsupported action', 400

    return flash_msg, 200
