from datetime import datetime
from typing import Optional

from configs import mod_conf
from db import db_m
from enums import DbPool, PostStatus, ReportCategory


async def get_all_reports() -> Optional[list[dict]]:
    if not (reports := await db_m.query_dict('SELECT * FROM reports;', p_id=DbPool.mod)):
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


async def create_report(board_shortname: str, num: int, submitter_ip: str,
                        submitter_notes: str, report_category: str,
                        report_status: str, moderator_notes: str = None) -> None:
    now = datetime.now()
    params = (
        board_shortname,
        num,
        mod_conf['default_reported_post_status'],
        submitter_ip,
        submitter_notes,
        report_category,
        report_status,
        moderator_notes,
        now,
        now,
    )
    sql_string = f"""
    INSERT INTO reports 
    (board_shortname, num, post_status, submitter_ip, submitter_notes,
    report_category, report_status, moderator_notes, created_at, last_updated_at)
    VALUES ({db_m.phg.size(params)});
    """
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def edit_report(report_id: int, post_status: str, report_status: str, moderator_notes: str) -> None:
    if not await get_report_by_id(report_id):
        return

    sql_string = """
    UPDATE reports
    SET post_status=∆, report_status=∆, moderator_notes=∆, last_updated_at=∆
    WHERE report_id=∆;
    """
    params = (post_status, report_status, moderator_notes, datetime.now(), report_id)
    await db_m.query_dict(sql_string, params=params, commit=True, p_id=DbPool.mod)


async def delete_report(report_id: int) -> None:
    if not (report := await get_report_by_id(report_id)):
        return
    await db_m.query_dict('DELETE FROM reports WHERE report_id=∆;', params=(report_id,), commit=True, p_id=DbPool.mod)


async def get_reports_by_report_status(report_status: str) -> Optional[list[dict]]:
    if not (reports := await db_m.query_dict('SELECT * FROM reports WHERE report_status=∆;', params=(report_status,), p_id=DbPool.mod)):
        return None
    return reports


async def get_reports_by_post_status(post_status: PostStatus) -> Optional[list[dict]]:
    if not (reports := await db_m.query_dict('SELECT * FROM reports WHERE post_status=∆;', params=(post_status,), p_id=DbPool.mod)):
        return None
    return reports


async def get_reports_by_category(report_category: ReportCategory) -> Optional[list[dict]]:
    if not (reports := await db_m.query_dict('SELECT * FROM reports WHERE report_category=∆;', params=(report_category,), p_id=DbPool.mod)):
        return None
    return reports
