from configs import archiveposting_conf
from db import db_a
from sidetables.tables_indexes import create_table_sqlite


async def init_archiveposting():
    await create_non_existing_tables()


sql_create_board = """
create table if not exists `%%BOARD%%` (
    doc_id integer not null primary key autoincrement,
    media_id integer not null,
    poster_ip text not null,
    num integer not null,
    subnum integer not null,
    thread_num integer not null,
    op integer not null,
    timestamp integer not null,
    timestamp_expired integer not null,
    preview_orig text,
    preview_w integer not null,
    preview_h integer not null,
    media_filename text,
    media_w integer not null,
    media_h integer not null,
    media_size integer not null,
    media_hash text,
    media_orig text,
    spoiler integer not null,
    deleted integer not null,
    capcode text not null,
    email text,
    name text,
    trip text,
    title text,
    comment text,
    delpass text,
    sticky integer not null,
    locked integer not null,
    poster_hash text,
    poster_country text,
    exif text
);"""

create_all_tables = sql_create_board + create_table_sqlite

async def create_non_existing_tables():
    if not archiveposting_conf['enabled']:
        return

    board = archiveposting_conf['board_name']
    try:
        sql = f'SELECT * FROM `{board}` LIMIT 1;'
        await db_a.query_tuple(sql)
        print(f'Archiveposting table [{board}] already exist.')
    except Exception:
        sqls = create_all_tables.replace('%%BOARD%%', board).split(';')
        for sql in sqls:
            await db_a.query_tuple(sql, commit=True)
        print(f'Archiveposting table [{board}] created.')
