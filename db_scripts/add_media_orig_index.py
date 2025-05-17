import sqlite3

db_path = '/mnt/ritual/ritual.db'
db_path = '/home/yy/Documents/backup_wallow/ritual.db'
boards = [
    '3','a','aco','adv','an','b','bant','biz','c','cgl','ck',
    'cm','co','d','diy','e','f','fa','fit','g','gd','gif','h','hc',
    'his','hm','hr','i','ic','int','jp','k','lgbt','lit','m','mlp','mu',
    'n','news','o','out','p','po','pol','pw','qa','qst','r','r9k','s','s4s',
    'sci','soc','sp','t','tg','toy','trv','tv','u','v','vg','vip','vm',
    'vmg','vp','vr','vrpg','vst','vt','w','wg','wsg','wsr','x','xs','y',
]

conn = sqlite3.connect(db_path)
cur = conn.cursor()

for board in boards:
    print(board)
    cur.execute("select name from sqlite_master where type='table' and name=?", (board,))
    if cur.fetchone():
        sql = f'create index if not exists idx_{board}_media_orig on `{board}`(media_orig);'
        cur.execute(sql)

conn.commit()
conn.close()
