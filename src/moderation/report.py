from datetime import datetime
from typing import Optional

from configs import mod_conf
from db import db_m
from enums import DbPool, ModStatus, PublicAccess, ReportCategory


async def get_all_reports(public_access: PublicAccess=None, mod_status: ModStatus=None) -> Optional[list[dict]]:
    ph = db_m.phg()
    where = []
    params = []

    if public_access:
        where.append(f'public_access = {ph}')
        params.append(public_access.value)

    if mod_status:
        where.append(f'mod_status = {ph}')
        params.append(mod_status.value)

    if where:
        where = 'where ' + ' and '.join(where)

    sql = f'select * from reports {where} order by created_at desc;'
    if not (reports := (await db_m.query_dict(sql, params=params, p_id=DbPool.mod))):
        return []
    return reports


async def get_report_by_id(report_id: int) -> Optional[dict]:
    if not (reports := await db_m.query_dict('SELECT * FROM reports WHERE report_id=∆;', params=(report_id,), p_id=DbPool.mod)):
        return
    return reports[0]


async def get_report_by_board(board_shortname: str) -> Optional[list[dict]]:
    if not (reports := await db_m.query_dict('SELECT * FROM reports WHERE board_shortname=∆;', params=(board_shortname,), p_id=DbPool.mod)):
        return
    return reports


async def get_report_by_post_num(board_shortname: str, num: int) -> Optional[list[dict]]:
    if not (reports := await db_m.query_dict('SELECT * FROM reports WHERE board_shortname=∆ and num=∆;', params=(board_shortname, num,), p_id=DbPool.mod)):
        return
    return reports


async def create_report(board_shortname: str, thread_num: int, num: int, op: int, submitter_ip: str,
                        submitter_notes: str, report_category: str,
                        mod_status: str, moderator_notes: str = None) -> None:
    now = datetime.now()
    params = (
        board_shortname,
        thread_num,
        num,
        op,
        mod_conf['default_reported_post_public_access'],
        submitter_ip,
        submitter_notes,
        report_category,
        mod_status,
        moderator_notes,
        now,
        now,
        0,
    )
    sql_string = f"""
    INSERT INTO reports 
    (board_shortname, thread_num, num, op, public_access, submitter_ip, submitter_notes,
    report_category, mod_status, moderator_notes, created_at, last_updated_at, user_id)
    VALUES ({db_m.phg.size(params)});
    """
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)



async def edit_report_if_exists(report_id: int, public_access: str=None, mod_status: str=None, moderator_notes: str=None) -> dict:
    if not (report := await get_report_by_id(report_id)):
        return {}

    s = ''
    params = []

    if public_access:
        s += ' public_access=∆, '
        params.append(public_access)
    if mod_status:
        s += ' mod_status=∆, '
        params.append(mod_status)
    if moderator_notes:
        s += ' moderator_notes=∆, '
        params.append(moderator_notes)

    if not s:
        return

    sql_string = f"""
    UPDATE reports
    SET {s} last_updated_at=∆
    WHERE report_id=∆;
    """
    params = params + [datetime.now(), report_id]
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)
    return report


async def delete_report_if_exists(report_id: int) -> dict:
    if not (report := await get_report_by_id(report_id)):
        return {}
    await db_m.query_dict('DELETE FROM reports WHERE report_id=∆;', params=(report_id,), commit=True, p_id=DbPool.mod)
    return report


async def get_reports_by_report_status(mod_status: str) -> Optional[list[dict]]:
    if not (reports := await db_m.query_dict('SELECT * FROM reports WHERE mod_status=∆;', params=(mod_status,), p_id=DbPool.mod)):
        return
    return reports


async def get_reports_by_post_status(public_access: PublicAccess) -> Optional[list[dict]]:
    if not (reports := await db_m.query_dict('SELECT * FROM reports WHERE public_access=∆;', params=(public_access,), p_id=DbPool.mod)):
        return
    return reports


async def get_reports_by_category(report_category: ReportCategory) -> Optional[list[dict]]:
    if not (reports := await db_m.query_dict('SELECT * FROM reports WHERE report_category=∆;', params=(report_category,), p_id=DbPool.mod)):
        return
    return reports
