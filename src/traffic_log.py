import sqlite3
from datetime import datetime, timezone
from time import perf_counter

from quart import Request, Response, g, request

from configs import traffic_log_conf

traffic_fields = [
    'x_forwarded_for',
    'remote_addr',
    'referrer',
    'method',
    'path',
    'query_string',
    'duration',
    'end_datetime_utc',
    'user_agent',
    'content_length',
    # 'accept',
    # 'accept_language',
    # 'accept_encoding',
    # 'origin',
    # 'content_md5',
    # 'scheme',
]
sql_insert_traffic_params = ','.join(['?'] * len(traffic_fields))
sql_insert_traffic = f"""insert into traffic ({','.join(traffic_fields)}) values ({sql_insert_traffic_params});"""

def insert_traffic_record(request: Request, duration: float):
    traffic_record = dict(
        x_forwarded_for=request.headers.get("X-Forwarded-For", None),
        remote_addr=request.headers.get("Remote-Addr", None),
        referrer=request.referrer,
        method=request.method,
        path=request.path,
        query_string=request.query_string.decode() if request.query_string else None,
        duration=duration,
        end_datetime_utc=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        user_agent=str(request.user_agent),
        content_length=request.content_length,
        # accept=request.headers.get("Accept", None),
        # accept_language=request.headers.get("Accept-Language", None),
        # accept_encoding=request.headers.get("Accept-Encoding", None),
        # origin=request.origin,
        # content_md5=request.content_md5,
        # scheme=request.scheme,
    )
    with sqlite3.connect(traffic_log_conf['database']) as db:
        db.execute(sql_insert_traffic, tuple(traffic_record.get(k) for k in traffic_fields))
        db.commit()


sql_create_traffic_table = """
create table if not exists traffic (
    id                  integer primary key autoincrement,
    x_forwarded_for     text,
    remote_addr         text,
    referrer            text,
    method              text,
    path                text,
    query_string        text,
    duration            real,
    end_datetime_utc    text,
    user_agent          text,
    content_length      integer
);
"""
# ,
# accept           text,
# accept_language  text,
# accept_encoding  text,
# origin           text,
# content_md5      text,
# scheme           text


def traffic_log_init():
    with sqlite3.connect(traffic_log_conf['database']) as db:
        db.execute(sql_create_traffic_table)
        db.commit()


traffic_log_enabled = traffic_log_conf.get('enabled')
ignore_path_startswith = traffic_log_conf.get('ignore_path_startswith')
def traffic_log_request_before():
    if traffic_log_enabled:
        if ignore_path_startswith and request.path.startswith(ignore_path_startswith):
            g.start_time = None
            return
        g.start_time = perf_counter()


def traffic_log_request_after(response: Response):
    if g.start_time:
        insert_traffic_record(request, round(perf_counter() - g.start_time, 5))
    return response
