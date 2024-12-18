import asyncio
from collections import defaultdict

from asagi_converter import (
    get_deleted_non_ops_by_board,
    get_deleted_ops_by_board
)
from boards import board_shortnames
from configs import mod_conf
from db import db_m
from enums import DbPool, UserRole
from moderation.user import create_user
from utils import make_src_path, read_file


async def init_memcache_bloom():
    pass


async def init_memcache_cuckoo():
    pass


async def init_memcache_sqlite():
    """For now, just use the moderation sqlite database."""
    moderation_scripts = ['board_nums_cache.sql']
    for script in moderation_scripts:
        await db_m.query_dict(read_file(make_src_path('moderation', 'sql', script)), p_id=DbPool.mod)

    bn_count = (await db_m.query_tuple('select count(*) bn_count from board_nums_cache;', p_id=DbPool.mod))[0]
    if bn_count:
        return
    
    pool = await db_m.pool_manager.get_pool(DbPool.mod)

    # marked as deleted from 4chan
    ph = db_m.phg()
    if mod_conf['hide_delete_posts'] and board_shortnames:
        for board in board_shortnames:
            op_nums, non_op_nums = await asyncio.gather(get_deleted_ops_by_board(board), get_deleted_non_ops_by_board(board))
            sql_op = f"""insert or ignore into board_nums_cache (board_shortname, num, op) values ('{board}', {ph}, 1)"""
            sql_non_op = f"""insert or ignore into board_nums_cache (board_shortname, num, op) values ('{board}', {ph}, 0)"""
            await pool.executemany(sql_op, op_nums)
            await pool.executemany(sql_non_op, non_op_nums)
            await pool.commit()

    # marked as deleted from archive moderation
    report_count = (await db_m.query_tuple('select board_shortname, post_num from reports;', p_id=DbPool.mod))
    if report_count:

    

async def init_moderation_db():
    moderation_scripts = ['users.sql', 'reports.sql', 'board_nums_cache.sql']
    for script in moderation_scripts:
        await db_m.query_dict(read_file(make_src_path('moderation', 'sql', script)), p_id=DbPool.mod)

    user_count = (await db_m.query_dict('select count(*) user_count from users;', p_id=DbPool.mod))[0].user_count
    if not user_count:
        admin_username = mod_conf['admin_user']
        admin_password = mod_conf['admin_password']

        await create_user(admin_username, admin_password, UserRole.admin, True, 'Remember to change your default password.')


async def filter_reported_posts(posts: list, remove_replies=False) -> list:
    """If remove_replies is True, then replies to deleted posts are removed."""
    if not posts:
        return posts

    board_and_nums = [(p['board_shortname'], p['num']) for p in posts]
    ph = ','.join([f'({db_m.phg()},{db_m.phg()})'] * len(board_and_nums))
    sql_string = f"""
        select board_shortname, num
        from board_nums_cache
        where (board_shortname, num) in ({ph})
    ;"""
    bad_boards_and_nums = await db_m.query_tuple(sql_string, board_and_nums)
    board_to_numset = defaultdict(set)
    for bbn in bad_boards_and_nums:
        board_to_numset[bbn[0]].add(bbn[1])

    i = 0
    while i < len(posts):
        post = posts[i]
        if post.board_shortname not in board_to_numset:
            i+=1
            continue
        if post.num not in board_to_numset[post.board_shortname]:
            i+=1
            continue
        
        posts.pop(i)

    return posts
