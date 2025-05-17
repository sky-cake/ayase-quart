"""Run this when you want to populate the tagger db with flag = 1 (asagi db contains the image) and note = board"""

import sqlite3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from boards import board_shortnames
from enums import DbType
from configs import db_tag_conf, db_conf


def needs_cascade(cursor, table_name):
    """Manually adding on delete cascade if no present in tag or image_tag tables
    is done with queries *similar to* the following,

        ALTER TABLE tag RENAME TO tag_old;

        CREATE TABLE ... (see src/tagging/db.py)

        INSERT INTO tag (pk, tag_id, tag_name, tag_type_id)
        SELECT pk, tag_id, tag_name, tag_type_id FROM tag_old;

        DROP TABLE tag_old;
    """
    # PRAGMA foreign_key_list(image_tag);
    # PRAGMA foreign_key_list(tag);
    cursor.execute(f'PRAGMA foreign_key_list({table_name});')
    fk_info = cursor.fetchall()
    for fk in fk_info:
        if fk[2] == 'image' and fk[6].lower() == 'cascade':
            return False
    return True


def process_databases(asagi_db_path, tagger_db_path, db1_table):
    conn1 = sqlite3.connect(asagi_db_path)
    conn2 = sqlite3.connect(tagger_db_path)
    cursor1 = conn1.cursor()
    cursor2 = conn2.cursor()

    cursor2.execute('PRAGMA table_info(image)')
    columns = [col[1] for col in cursor2.fetchall()]

    print(columns)

    if 'note' in columns and 'board' not in columns:
        cursor2.execute('ALTER TABLE image RENAME COLUMN note TO board')
        conn2.commit()

    if 'image_path' in columns and 'filename' not in columns:
        cursor2.execute('ALTER TABLE image RENAME COLUMN image_path TO filename')
        cursor2.execute("UPDATE image SET filename = SUBSTR(filename, INSTR(filename, '/image/') + 15) WHERE filename like '%/image/%'")
        conn2.commit()

    chunk_size = 10_000

    cursor1.execute(f'SELECT COUNT(*) FROM {db1_table} WHERE media_orig IS NOT NULL')
    total_records = cursor1.fetchone()[0]

    offset = 0
    while offset < total_records:
        s = f'SELECT media_orig FROM {db1_table} WHERE media_orig IS NOT NULL LIMIT {chunk_size} OFFSET {offset}'
        cursor1.execute(s)

        params = [(row[0],) for row in cursor1.fetchall()]

        s = f"""UPDATE image SET board = '{db1_table}' WHERE filename = ?"""
        if params:
            cursor2.executemany(s, params)
            conn2.commit()

        offset += chunk_size
        print(f"Processed {min(offset, total_records)} of {total_records} records")

    conn2.commit()

    conn1.close()
    conn2.close()
    print("Processing complete")

if __name__ == "__main__":
    asagi_db_path = db_conf['database']
    tagger_db_path = db_tag_conf['database']

    print(f'{asagi_db_path=}')
    print(f'{tagger_db_path=}')
    ans = input('Looks good? (y/n)')

    if ans == 'y':
        if db_conf['db_type'] != DbType.sqlite:
            raise NotImplementedError

        for board in board_shortnames:
            print(f'Migrating {board=}...')
            try:
                process_databases(asagi_db_path, tagger_db_path, board)
                print(f'Done migrating: {board}')
            except sqlite3.Error as e:
                print(f"An error occurred: {e}")