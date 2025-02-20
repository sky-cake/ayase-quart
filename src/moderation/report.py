from datetime import datetime
from typing import Optional

from quart import abort
from quart_auth import AuthUser

from moderation.user import Permissions

from asagi_converter import get_post, move_post_to_delete_table
from configs import mod_conf
from db import db_m
from enums import DbPool, ModStatus, PublicAccess, SubmitterCategory, ReportAction
from leafs import post_files_delete, post_files_hide, post_files_show
from moderation.filter_cache import fc
from moderation.user import Permissions


async def get_report_count_all() -> int:
    sql = f"""
        select
            count(*) as report_count
        from report_parent
    """
    if (reports := (await db_m.query_dict(sql, p_id=DbPool.mod))):
        return reports[0]['report_count']
    return 0


async def get_report_count_f(public_access: PublicAccess=None, mod_status: ModStatus=None, board_shortnames: list[str]=None) -> Optional[list[dict]]:
    ph = db_m.phg()
    where = []
    params = []

    if public_access:
        where.append(f'public_access = {ph}')
        params.append(public_access.value)

    if mod_status:
        where.append(f'mod_status = {ph}')
        params.append(mod_status.value)

    if board_shortnames:
        where.append(f'board_shortname in ({db_m.phg.qty(len(board_shortnames))})')
        params.extend(board_shortnames)

    if where:
        where = 'where ' + ' and '.join(where)

    sql = f"""
        select
            count(*) report_count
        from report_parent
            join report_child using (report_parent_id)
        {where}
    """
    if (reports := (await db_m.query_dict(sql, params=params, p_id=DbPool.mod))):
        return reports[0]['report_count']
    return 0


async def get_reports_f(public_access: PublicAccess=None, mod_status: ModStatus=None, board_shortnames: list[str]=None, page_num: int=0, page_size: int=20) -> Optional[list[dict]]:
    ph = db_m.phg()
    where = []
    params = []

    if public_access:
        where.append(f'public_access = {ph}')
        params.append(public_access.value)

    if mod_status:
        where.append(f'mod_status = {ph}')
        params.append(mod_status.value)

    if board_shortnames:
        where.append(f'board_shortname in ({db_m.phg.qty(len(board_shortnames))})')
        params.extend(board_shortnames)

    if where:
        where = 'where ' + ' and '.join(where)

    offset = ''
    if page_size:
         offset = f'limit {int(page_size)} offset {int(page_num)}'

    sql = f"""
        select
            report_parent_id,
            board_shortname,
            num,
            thread_num,
            public_access,
            mod_status,
            mod_notes,
            count(submitter_ip) as report_count,
            group_concat(submitter_category, '||') as submitter_category,
            group_concat(submitter_notes, '||') as submitter_notes
        from report_parent
            join report_child using (report_parent_id)
        {where}
        group by 1,2,3,4,5,6,7
        order by created_at desc
        {offset}
    """
    if (reports := (await db_m.query_dict(sql, params=params, p_id=DbPool.mod))):
        return reports
    return []


async def get_report_by_id(report_parent_id: int) -> Optional[dict]:
    if (reports := await db_m.query_dict(f'select * from report_parent where report_parent_id={db_m.phg()};', params=(report_parent_id,), p_id=DbPool.mod)):
        return reports[0]


async def get_report_by_board(board_shortname: str) -> Optional[list[dict]]:
    if (reports := await db_m.query_dict(f'select * from report_parent where board_shortname={db_m.phg()};', params=(board_shortname,), p_id=DbPool.mod)):
        return reports


async def get_report_by_post_num(board_shortname: str, num: int) -> Optional[list[dict]]:
    if (reports := await db_m.query_dict(f'select * from report_parent where board_shortname={db_m.phg()} and num={db_m.phg()};', params=(board_shortname, num,), p_id=DbPool.mod)):
        return reports


async def get_report_parent_id(board_shortname: str, num: int) -> Optional[int]:
    report_parent_id = None
    ph = db_m.phg()
    sql = f'select report_parent_id from report_parent where board_shortname = {ph} and num = {ph};'
    rows = await db_m.query_dict(sql, params=[board_shortname, num], p_id=DbPool.mod)
    if rows:
        report_parent_id = rows[0]['report_parent_id']
    return report_parent_id


async def create_report(
    board_shortname: str,
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
    public_access = mod_conf['default_reported_post_public_access']

    report_parent_id = await get_report_parent_id(board_shortname, num)

    if not report_parent_id:
        params_parent = [board_shortname, num, thread_num, op, mod_status, public_access, mod_notes, now]
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


async def get_reports_by_mod_status(mod_status: ModStatus) -> Optional[list[dict]]:
    sql = f'select * report_parent from report_parent where mod_status={db_m.phg()};'
    if (reports := await db_m.query_dict(sql, params=(mod_status.value,), p_id=DbPool.mod)):
        return reports


async def get_reports_by_public_access(public_access: PublicAccess) -> Optional[list[dict]]:
    sql = f'select * from report_parent where public_access={db_m.phg()};'
    if (reports := await db_m.query_dict(sql, params=(public_access.value,), p_id=DbPool.mod)):
        return reports


async def get_reports_by_submitter_category(submitter_category: SubmitterCategory) -> Optional[list[dict]]:
    sql = f"""
    select *
    from report_parent
    where report_parent_id in (select report_parent_id from report_child where submitter_category={db_m.phg()})
    ;"""
    if (reports := await db_m.query_dict(sql, params=(submitter_category.value,), p_id=DbPool.mod)):
        return reports


async def reports_action_routine(current_usr: AuthUser, report_parent_id: int, action: str, mod_notes: str=None) -> tuple[str, int]:

    report = await get_report_by_id(report_parent_id)
    if not report:
        return f'Could not find report with id {report_parent_id}.', 404

    flash_msg = ''

    match action:
        case ReportAction.report_delete:
            if not current_usr.has_permissions([Permissions.report_delete]):
                return f'Need permissions for {Permissions.report_delete.name}', 401

            report = await delete_report_if_exists(report_parent_id)
            flash_msg = f'Report seems to already be deleted.'
            if report:
                await fc.delete_post(report['board_shortname'], report['num'], report['op'])
                flash_msg = f'Report deleted.'
            return flash_msg, 200

        case ReportAction.post_delete:
            if not current_usr.has_permissions([Permissions.post_delete]):
                return f'Need permissions for {Permissions.post_delete.name}', 401
            
            # Note: do not delete the report here. It is still needed to filter outgoing posts from full text search.
            post, flash_msg = await move_post_to_delete_table(report.board_shortname, report.num)
            if not post:
                return 'Could not find post. ' + flash_msg, 404

            full_del, prev_del = post_files_delete(post)
            flash_msg += ' Deleted full media.' if full_del else ' Did not delete full media.'
            flash_msg += ' Deleted thumbnail.' if prev_del else ' Did not delete thumbnail.'

        case ReportAction.media_delete:
            if not current_usr.has_permissions([Permissions.media_delete]):
                return f'Need permissions for {Permissions.media_delete.name}', 401

            post = await get_post(report.board_shortname, report.num)
            if not post:
                return 'Could not find post.', 404
            full_del, prev_del = post_files_delete(post)
            flash_msg += ' Deleted full media.' if full_del else ' Did not delete full media.'
            flash_msg += ' Deleted thumbnail.' if prev_del else ' Did not delete thumbnail.'

        case ReportAction.media_hide:
            if not current_usr.has_permissions([Permissions.media_hide]):
                return f'Need permissions for {Permissions.media_hide.name}', 401

            post = await get_post(report.board_shortname, report.num)
            if not post:
                return 'Could not find post.', 404
            full_hid, prev_hid = post_files_hide(post)
            flash_msg += ' Hid full media.' if full_hid else ' Did not hide full media.'
            flash_msg += ' Hid thumbnail.' if prev_hid else ' Did not hide thumbnail.'

        case ReportAction.media_show:
            if not current_usr.has_permissions([Permissions.media_show]):
                return f'Need permissions for {Permissions.media_show.name}', 401
            
            post = await get_post(report.board_shortname, report.num)
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
            flash_msg = f'Post now publicly visible.'

            if mod_conf.get('hidden_images_path'):
                post = await get_post(report.board_shortname, report.num)
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
                post = await get_post(report.board_shortname, report.num)
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
            flash_msg = f'Report had their moderation notes saved.'

        case _:
            return 'Unsupported action', 400

    return flash_msg, 200