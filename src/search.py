from db import query_execute, db_pool_close
from collections import defaultdict
from search_providers.baseprovider import BaseSearch
from orjson import dumps
from asagi_converter import get_text_quotelinks, get_selector
from asyncio import sleep, run
import logging

async def index_board(board: str, search_provider: BaseSearch):
    wait_cycle = 5
    logger = logging.getLogger('search-index')
    async for thread_nums in get_board_threads(board):
        logger.warning(f'processing {board} threads: {thread_nums[0]}-{thread_nums[-1]}')
        posts = await get_thread_posts(board, thread_nums)
        while not await search_provider.posts_ready():
            logger.warning(f'wait indexing {wait_cycle}s')
            await sleep(wait_cycle)
        await search_provider.add_posts(posts)

def get_filter_selector(board: str):
    return f'''
    select
        doc_id,
        num,
        '{board}' as board,
        thread_num,
        title,
        comment,
        media_filename,
        media_hash,
        timestamp,
        op,
        deleted
    '''

async def get_thread_posts(board: str, thread_nums: list[int]):
    thread_nums = tuple(set(thread_nums))
    
    filter_q = f'''
    {get_filter_selector(board)},
    `media`,`preview_reply`,`preview_op`
    FROM `{board}`
    left join `{board}_images` using (media_hash)
    where thread_num in %s order by num asc
    ;'''
    post_q = f'{get_selector(board)} from `{board}` where thread_num in %s order by num asc'
    post_rows = await query_execute(post_q, params=(thread_nums,))
    filter_rows = await query_execute(filter_q, params=(thread_nums,))
    reply_lookup = get_reply_lookup(post_rows)
    posts = []
    for p_row, f_row in zip(post_rows, filter_rows):
        set_image(p_row, f_row)
        p_row['replies'] = reply_lookup.get(p_row.num, [])
        del p_row['com']
        f_row['data'] = dumps(p_row).decode()
        f_row['op'] = bool(f_row['op'])
        f_row['deleted'] = bool(f_row['deleted'])
        del f_row['media']
        del f_row['preview_reply']
        del f_row['preview_op']
        posts.append(f_row)
    return posts
    
def get_reply_lookup(rows):
    replies = defaultdict(list)
    for row in rows:
        if not row.comment:
            continue
        for quotelink in get_text_quotelinks(row.comment):
            replies[int(quotelink)].append(row.doc_id)
    return replies

def set_image(p_row, f_row):
    if(p_row["resto"] == 0):
        p_row["asagi_preview_filename"] = f_row["preview_op"]
    else:
        p_row["asagi_preview_filename"] = f_row["preview_reply"]

    p_row["asagi_filename"] = f_row["media"]

async def get_board_threads(board: str):
    batch_threads = 1000
    next_batch = lambda after: f'thread_num > {after}'
    after = 0
    while True:
        q = f"SELECT thread_num FROM {board}_threads where {next_batch(after)} order by thread_num asc limit {batch_threads};"
        rows = await query_execute(q, )
        if not rows:
            break
        yield [row.thread_num for row in rows]
        if len(rows) < batch_threads:
            break

        after = rows[-1].thread_num

async def main(args):
    if len(args) < 1:
        print('python -m search board1 [board2 [board3 [...]]]')
        sys.exit()
    from configs import CONSTS
    for a in args:
        if not a in CONSTS.board_shortnames:
            print(f'invalid board {a}')
            sys.exit()
    from search_providers import get_search_provider
    sp = get_search_provider()
    for board in args:
        await index_board(board, sp)
    await db_pool_close()

if __name__ == "__main__":
    import sys
    run(main(sys.argv[1:]))