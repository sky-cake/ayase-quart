import sqlite3
import os
import tqdm

media_orig_dir = '/mnt/dl/g/image'
media_thumb_dir = '/mnt/dl/g/thumb'

db_path = '/home/yy/Desktop/ritual_2025_05_08.db'
db_path = '/mnt/ritual/ritual.db'

regex0so_path = '/home/yy/Desktop/regex0.so'
regex0so_path = '/mnt/regex0.so'


sql = """
    select media_orig
    from g
    where
    thread_num in (
        select thread_num
        from g
        where
        op = 1
        and title is not null
        and title regexp '/lmg|/ldg|/de3|/sdg|/aicg|/wait|deepseek|/adg'
    )
    and media_orig is not null
"""


conn = sqlite3.connect(db_path)
conn.enable_load_extension(True)
conn.load_extension(regex0so_path)
cursor = conn.execute(sql)

try:
    rows = cursor.fetchall()

    sql = '''DELETE FROM image WHERE board = ? AND filename = ?'''
    cursor.executemany(sql, [('g', row[0]) for row in rows])
    conn.commit()

    print(f"{len(rows)} entries found.")
    ans = input('Continue? (y/n): ')
    assert ans.strip().lower() == 'y'

    exts = {'webm', 'gif', 'mp4', 'png', 'jpeg', 'jpg'}

    for row in tqdm.tqdm(rows):

        media_orig = row[0]
        if not media_orig:
            continue

        if '.' not in media_orig:
            raise ValueError(f"Missing extension: {media_orig}")

        name, ext = media_orig.rsplit('.', 1)
        ext = ext.lower()

        if not name or ext not in exts:
            raise ValueError(f"Invalid media file: {media_orig}")

        try:
            orig_path = os.path.join(media_orig_dir, name[:4], name[4:6], media_orig)
            if os.path.isfile(orig_path):
                os.remove(orig_path)

            thumb_path = os.path.join(media_thumb_dir, name[:4], name[4:6], f'{name}s.jpg')
            if os.path.isfile(thumb_path):
                os.remove(thumb_path)
        except Exception as io_err:
            print(f"Error processing {media_orig}: {io_err}")

except Exception as e:
    print(f"Error: {e}")
finally:
    cursor.close()
    conn.close()
