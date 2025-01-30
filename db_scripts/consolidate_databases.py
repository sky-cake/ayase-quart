from textwrap import dedent

import pandas as pd
from sqlalchemy import create_engine, text


def execute_query(sql, db_old='', db_new='', board='', write=False, print_output=True):
    """Users of this function must specify if a read or write query is executed by using the kwarg `write`."""

    with ENGINE.connect() as conn:
        sql = dedent(sql.format(db_old=db_old, db_new=db_new, board=board))

        if not write:
            result = pd.read_sql(sql, conn)

            if print_output:
                print(result)

            return result

        conn.execute(text(sql))
        conn.commit()


def drop_modification_columns(db_old, db_new, board):
    sqls = [
        """ALTER TABLE {db_new}.{board} DROP COLUMN modified_doc_id;""",
        """ALTER TABLE {db_new}.{board} DROP COLUMN modified_media_id;""",
        """ALTER TABLE {db_new}.{board}_images DROP COLUMN modified_media_id;""",
    ]
    for sql in sqls:
        try:
            r = execute_query(sql, db_old, db_new, board, write=True)
        except:
            pass


def find_duplicate_post_num(db_old, db_new, board):
    sqls = [
        """select num, count(*) from {db_old}.{board} group by num having count(*) > 1;""",
        """select num, count(*) from {db_new}.{board} group by num having count(*) > 1;""",
    ]
    for sql in sqls:
        r = execute_query(sql, db_old, db_new, board, print_output=True)
        assert len(r) == 0


def find_colliding_post_num(db_old, db_new, board):
    """Find records to be deleted from old database"""

    sql = """select * from {db_old}.{board} inner join {db_new}.{board} on {db_old}.{board}.num = {db_new}.{board}.num;"""
    return execute_query(sql, db_old, db_new, board)


def is_table(db, board):
    s = """select * from information_schema.tables WHERE table_schema = '{db}' AND table_name = '{board}' LIMIT 1;""".format(db=db, board=board)
    r = execute_query(s, board=board, print_output=False)
    return len(r) > 0


def is_valid_table(db_old, db_new, board):
    if not is_table(db_new, board):
        print(f'TABLE DOES NOT EXIST: {db_new}.{board}')
        return False

    if not is_table(db_old, board):
        return False  # raise NotImplementedError('We will need to copy the new database table directly over to the old database.')

    return True


def do_query_sequence(db_old, db_new, board):

    find_duplicate_post_num(db_old, db_new, board)
    collisions = find_colliding_post_num(db_old, db_new, board)
    assert len(collisions) >= 0  # this is not really needed here, but it's nice to see what it returns

    if len(collisions) > 0:
        sql = """DELETE from {db_old}.{board} where {db_old}.{board}.num in (select num from (select {db_old}.{board}.num from {db_old}.{board} inner join {db_new}.{board} on {db_old}.{board}.num = {db_new}.{board}.num) as required_alias);"""
        execute_query(sql, db_old, db_new, board, write=True)

        assert len(find_colliding_post_num(db_old, db_new, board)) == 0

    drop_modification_columns(db_old, db_new, board)

    # Make new database PK/FKs higher than old database keys
    # We add 10 above the old database keys for good measure
    sqls = [
        """ALTER TABLE {db_new}.{board} ADD COLUMN modified_doc_id INT UNSIGNED NOT NULL;""",
        """UPDATE {db_new}.{board} SET modified_doc_id = doc_id + (select max(doc_id) from {db_old}.{board}) + 10;""",
        """ALTER TABLE {db_new}.{board}_images ADD COLUMN modified_media_id INT UNSIGNED NOT NULL;""",
        """UPDATE {db_new}.{board}_images SET modified_media_id = media_id + (select max(media_id) from {db_old}.{board}_images) + 10;""",
        """ALTER TABLE {db_new}.{board} ADD COLUMN modified_media_id INT UNSIGNED NOT NULL;""",
        """UPDATE {db_new}.{board} inner join {db_new}.{board}_images on {db_new}.{board}.media_id = {db_new}.{board}_images.media_id and {db_new}.{board}.media_id > 0 SET {db_new}.{board}.modified_media_id = {db_new}.{board}_images.modified_media_id WHERE {db_new}.{board}.media_id = {db_new}.{board}_images.media_id;""",
        """UPDATE {db_old}.{board}_images inner join {db_new}.{board}_images on {db_old}.{board}_images.media_hash = {db_new}.{board}_images.media_hash SET {db_old}.{board}_images.media_id = {db_new}.{board}_images.modified_media_id WHERE {db_old}.{board}_images.media_hash = {db_new}.{board}_images.media_hash;""",
        """DELETE from {db_new}.{board}_images where {db_new}.{board}_images.media_hash in ( select media_hash from (select {db_new}.{board}_images.media_hash from {db_new}.{board}_images inner join {db_old}.{board}_images on {db_new}.{board}_images.media_hash = {db_old}.{board}_images.media_hash) as media_collisions);""",
    ]
    for sql in sqls:
        execute_query(sql, db_old, db_new, board, write=True)

    # Make sure there are no media_hash collisions between databases now that we've addressed them
    sql = """select {db_new}.{board}_images.media_hash from {db_new}.{board}_images inner join {db_old}.{board}_images on {db_new}.{board}_images.media_hash = {db_old}.{board}_images.media_hash;"""
    assert len(execute_query(sql, db_old, db_new, board)) == 0

    # Throw the new database data into the remaining old database
    sql = """INSERT INTO {db_old}.{board}  (
        doc_id,
        media_id,
        poster_ip, num, subnum, thread_num, op, timestamp, timestamp_expired,
        preview_orig, preview_w, preview_h, media_filename, media_w, media_h, media_size,
        media_hash, media_orig, spoiler, deleted, capcode, email, name, trip, title, comment,
        delpass, sticky, locked, poster_hash, poster_country, exif
    ) SELECT 
        modified_doc_id,
        modified_media_id,
        poster_ip, num, subnum, thread_num, op, timestamp, timestamp_expired,
        preview_orig, preview_w, preview_h, media_filename, media_w, media_h, media_size,
        media_hash, media_orig, spoiler, deleted, capcode, email, name, trip, title, comment,
        delpass, sticky, locked, poster_hash, poster_country, exif
    FROM {db_new}.{board};"""
    execute_query(sql, db_old, db_new, board, write=True)

    sql = """INSERT INTO {db_old}.{board}_images  (
        media_id,
        media_hash,
        media,
        preview_op,
        preview_reply,
        total,
        banned
    ) SELECT 
        modified_media_id,
        media_hash,
        media,
        preview_op,
        preview_reply,
        total,
        banned
    FROM {db_new}.{board}_images;"""
    execute_query(sql, db_old, db_new, board, write=True)

    drop_modification_columns(db_old, db_new, board)

    find_duplicate_post_num(db_old, db_new, board)


def get_row_count(db_old, db_new, board, message):
    sql = """
    SELECT 'new' as target, '{db_new}' as db, '{board}' as board, count(*) as records from {db_new}.{board}
    union
    SELECT 'old' as type, '{db_old}' as db, '{board}' as board, count(*) as records from {db_old}.{board};"""

    sql = sql.format(db_old=db_old, db_new=db_new, board=board)

    df = execute_query(sql, '', '', board)
    df['message'] = message
    return df


def main():
    results = []
    for board in boards:
        if not is_valid_table(db_old, db_new, board):
            continue

        df = get_row_count(db_old, db_new, board, 'before')
        results.append(df)

        do_query_sequence(db_old, db_new, board)

        df = get_row_count(db_old, db_new, board, 'after')
        results.append(df)

    df = pd.concat(results, ignore_index=True)
    df = df.sort_values(['board', 'target'], ignore_index=True, ascending=[True, False])
    print(df)


if __name__ == '__main__':
    input('Consider testing this on some test databases before the real deal.\n\n')

    host = ''
    user = ''
    password = ''
    db_old = 'hayden'
    db_new = 'neo'  # The `db_new` overwrites the `db_old` data when there are PK/FK collisions.
    boards = [
        'g',
        'ck',
    ]
    ENGINE = create_engine(f"mysql://{user}:{password}@{host}", echo=True)
    main()
