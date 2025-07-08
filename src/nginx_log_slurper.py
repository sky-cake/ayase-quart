import time
import sqlite3
import json
import os
from sqlite3 import Connection
import sys


def setup_db(db_path: str) -> Connection:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS traffic (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            xff TEXT,
            ip TEXT,
            ref TEXT,
            m TEXT,
            code TEXT,
            uri TEXT,
            q TEXT,
            unix REAL,
            local TEXT,
            dur REAL,
            ua TEXT,
            bsent INTEGER
        )
    ''')
    conn.commit()
    return conn


sql_insert = '''INSERT INTO traffic (xff, ip, ref, m, code, uri, q, unix, local, dur, ua, bsent)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
'''
def insert(conn: Connection, log_data: dict) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_insert, (
        log_data.get('xff'),
        log_data.get('ip'),
        log_data.get('ref'),
        log_data.get('m'),
        log_data.get('code'),
        log_data.get('uri'),
        log_data.get('q'),
        float(log_data.get('unix', 0)),
        log_data.get('local'),
        float(log_data.get('dur', 0)),
        log_data.get('ua'),
        int(log_data.get('bsent', 0))
    ))
    conn.commit()


def watch(log_path: str, conn: Connection, sleep_time: float = 1.0, start_at_end: bool=True):
    first = True
    count = 0
    with open(log_path, 'r') as f:
        if start_at_end:
            f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if line:
                try:
                    log_data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                insert(conn, log_data)
                count += 1
                continue
            
            if first:
                print(f'Slurped {count} valid json lines.')
            first = False
            time.sleep(sleep_time)


# Works with the NGINX Access log_format:

#   log_format jaysun escape=json '{'
#     '"xff":"$http_x_forwarded_for",'
#     '"ip":"$remote_addr",'
#     '"ref":"$http_referer",'
#     '"m":"$request_method",'
#     '"code":"$status",'
#     '"uri":"$uri",'
#     '"q":"$query_string",'
#     '"unix":"$msec",'
#     '"local":"$time_local",'
#     '"dur":"$request_time",'
#     '"ua":"$http_user_agent",'
#     '"bsent":"$body_bytes_sent"'
#   '}';

if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise ValueError("""
        Usage:   python     nginx_log_slurper.py <log_path: str>           <db_path: str>           <start_at_end: 0, 1>
        Example: python3.12 nginx_log_slurper.py /var/log/nginx/access.log /mnt/logs/aq_traffic2.db 0
        """)

    log_path = sys.argv[1]
    db_path = sys.argv[2]
    start_at_end = int(sys.argv[3]) == 1

    conn = setup_db(db_path)
    try:
        watch(log_path, conn, sleep_time=1.0, start_at_end=start_at_end)
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()
