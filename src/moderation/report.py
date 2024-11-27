from datetime import datetime

from db import db_m


def get_open_reports():
    sql_string = """SELECT * FROM reports WHERE status = 'open';"""
    return db_m.query_dict(sql_string)


def delete_report(report_id):
    db_m.query_dict("DELETE FROM reports WHERE report_id=?", params=(report_id,), commit=True)


def get_report_with_id(report_id):
    return db_m.query_dict("SELECT * FROM reports WHERE report_id=?", params=(report_id,))


def edit_report(post_no, category, details, status):
    sql_string = """
    UPDATE reports
    SET post_no=?, category=?, details=?, status=?, last_updated_datetime=?
    WHERE report_id=?;
    """
    params = (post_no, category, details, status, datetime.now())
    db_m.query_dict(sql_string, params, commit=True)
