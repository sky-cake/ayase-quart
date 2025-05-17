import os
import sqlite3


def scan_and_store(root_path, db_conn, board, batch_size=10_000):
    cur = db_conn.cursor()

    image_dir = os.path.join(root_path, board, 'image')
    thumb_dir = os.path.join(root_path, board, 'thumb')

    if not os.path.isdir(image_dir):
        return

    batch = []
    count = 0

    sql = '''
    INSERT INTO image (board, filename, ext, has_thumb)
            VALUES (?,?,?,?)
        ON CONFLICT(board, filename)
    DO UPDATE
        SET
            ext = excluded.ext,
            has_thumb = excluded.has_thumb
    '''

    for _, _, filenames in os.walk(image_dir):
        for filename in filenames:
            if '.' not in filename:
                continue

            name, ext = filename.rsplit('.', 1)

            thumb_path = os.path.join(thumb_dir, name[:4], name[4:6], f'{name}s.jpg')
            has_thumb = 1 if os.path.isfile(thumb_path) else 0

            batch.append((board, filename, ext, has_thumb))
            count += 1

            if len(batch) >= batch_size:
                print(f'images: {count:,}')

                cur.executemany(sql, batch)
                db_conn.commit()
                batch.clear()

    if batch:
        cur.executemany(sql, batch)
        db_conn.commit()


def main():
    boards = [
        '3','a','aco','adv','an','b','bant','biz','c','cgl','ck',
        'cm','co','d','diy','e','f','fa','fit','g','gd','gif','h','hc',
        'his','hm','hr','i','ic','int','jp','k','lgbt','lit','m','mlp','mu',
        'n','news','o','out','p','po','pol','pw','qa','qst','r','r9k','s','s4s',
        'sci','soc','sp','t','tg','toy','trv','tv','u','v','vg','vip','vm',
        'vmg','vp','vr','vrpg','vst','vt','w','wg','wsg','wsr','x','xs','y',
    ]

    root_path = '/mnt/dl'
    db_path = '/mnt/ritual/ritual.db'
    assert os.path.isfile(db_path)
    conn = sqlite3.connect(db_path)

    try:
        for board in boards:
            print(board)
            scan_and_store(root_path, conn, board)
        print('success')
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
