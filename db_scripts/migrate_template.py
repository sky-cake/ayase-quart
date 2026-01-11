import sqlite3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from boards import board_shortnames
from enums import DbType
from configs import db_conf


def process_databases(old_db_path, tagger_db_path, board):
    conn1 = sqlite3.connect(old_db_path)
    conn2 = sqlite3.connect(tagger_db_path)
    cursor1 = conn1.cursor()
    cursor2 = conn2.cursor()

    chunk_size = 10_000

    cursor1.execute(f"""
        SELECT COUNT(*)
        FROM image
        WHERE image_path LIKE '/mnt/dl/{board}/image/%'
    """)
    total_records = cursor1.fetchone()[0]
    print(f'{total_records=}')

    offset = 0
    while offset < total_records:
        cursor1.execute(f"""
            SELECT
                image_id,
                substr(image_path, {24 + len(board)}) AS filename,
                sha256,
                explicit,
                sensitive,
                questionable,
                general
            FROM image
            WHERE image_path LIKE '/mnt/dl/{board}/image/%'
            LIMIT {chunk_size}
            OFFSET {offset}
        """)
        rows = cursor1.fetchall()

        for old_image_id, filename, sha256, explicit, sensitive, questionable, general in rows:
            # Insert into image table (let SQLite assign image_id)
            cursor2.execute("""
                INSERT OR IGNORE INTO image
                (filename, sha256, explicit, sensitive, questionable, general, board)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (filename, sha256, explicit, sensitive, questionable, general, board))

            # Retrieve new image_id based on sha256
            cursor2.execute("SELECT image_id FROM image WHERE sha256 = ?", (sha256,))
            result = cursor2.fetchone()
            if result is None:
                print(f"[ERROR] Failed to find inserted image for sha256={sha256}")
                continue

            new_image_id = result[0]

            # Get tags from old DB
            cursor1.execute("""
                SELECT tag_id, prob
                FROM image_tag
                WHERE image_id = ?
            """, (old_image_id,))
            tag_rows = cursor1.fetchall()

            if tag_rows:
                # Insert with new image_id
                tag_data = [(new_image_id, tag_id, prob) for tag_id, prob in tag_rows]
                cursor2.executemany("""
                    INSERT OR IGNORE INTO image_tag
                    (image_id, tag_id, prob)
                    VALUES (?, ?, ?)
                """, tag_data)

                # Verify
                cursor2.execute("SELECT COUNT(*) FROM image_tag WHERE image_id = ?", (new_image_id,))
                inserted_count = cursor2.fetchone()[0]
                if inserted_count < len(tag_rows):
                    print(f"[WARNING] Only {inserted_count}/{len(tag_rows)} tags inserted for sha256={sha256}")
            else:
                print(f"[NOTE] No tags found for sha256={sha256}")

        conn2.commit()
        offset += chunk_size
        print(f"Processed {min(offset, total_records)} of {total_records} records")

    conn1.close()
    conn2.close()
    print("Processing complete")
    return


if __name__ == "__main__":
    old_db_path = '/home/yy/Desktop/image_400k.db'
    tagger_db_path = '/home/yy/Desktop/image.db'

    print(f'{old_db_path=}')
    print(f'{tagger_db_path=}')

    if db_conf['db_type'] != DbType.sqlite:
        raise NotImplementedError("Only sqlite is supported")

    for board in board_shortnames:
        print(f'Migrating {board=}...')
        try:
            process_databases(old_db_path, tagger_db_path, board)
            print(f'Done migrating: {board}')
        except sqlite3.Error as e:
            print(f"An error occurred while migrating {board}: {e}")
