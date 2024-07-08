from asyncio import run
from collections import defaultdict
from itertools import batched

from orjson import dumps
from quart import current_app
from tqdm.asyncio import tqdm

from asagi_converter import get_selector, get_text_quotelinks
from search_providers.baseprovider import BaseSearch


async def index_board(board: str, search_provider: BaseSearch):
    post_batch_size = 50_000

    async for thread_nums in tqdm(get_board_threads(board)):
        posts = await get_thread_posts(board, thread_nums)

        for post_batch in batched(posts, post_batch_size):
            await search_provider.add_posts(post_batch)


def get_filter_selector(board: str):
    return f"""
    SELECT
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
    """


async def get_thread_posts(board: str, thread_nums: list[int]):
    thread_nums = tuple(set(thread_nums))
    placeholders = ','.join(['%s'] * len(thread_nums)) # we do this because, "sqlite3.ProgrammingError: Error binding parameter 1: type 'tuple' is not supported"

    filter_q = f"""{get_filter_selector(board)}, `media`, `preview_reply`, `preview_op`
    FROM `{board}`
        LEFT JOIN `{board}_images` using (media_hash)
    WHERE thread_num IN ({placeholders})
    ORDER BY num ASC
    ;"""

    post_q = f"""{get_selector(board)}
    FROM `{board}`
    WHERE thread_num IN ({placeholders})
    ORDER BY num ASC
    ;"""

    post_rows = await current_app.db.query_execute(post_q, params=thread_nums)
    filter_rows = await current_app.db.query_execute(filter_q, params=thread_nums)
    reply_lookup = get_reply_lookup(post_rows)
    posts = []
    for p_row, f_row in zip(post_rows, filter_rows):
        set_image(p_row, f_row)
        p_row['replies'] = reply_lookup.get(p_row.num, [])
        del p_row['com']
        f_row['data'] = dumps(p_row).decode()
        f_row['op'] = bool(f_row['op'])
        f_row['deleted'] = bool(f_row['deleted'])
        f_row['pk'] = f'{board}-{f_row["doc_id"]}'
        del f_row['doc_id']
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
        rows = await current_app.db.query_execute(q, )
        if not rows:
            break
        yield [row.thread_num for row in rows]
        if len(rows) < batch_threads:
            break

        after = rows[-1].thread_num


async def main(args):
    """Demonstrates how to do an ad-hoc query against the context dependent db."""

    if len(args) < 1:
        print('python3 -m search board1 [board2 [board3 [...]]]')
        sys.exit()

    from configs import CONSTS
    for a in args:
        if not a in CONSTS.board_shortnames:
            print(f'Invalid board: {a}')
            sys.exit()

    from search_providers import get_search_provider
    async def index_boards():
        sp = get_search_provider()
        for board in args:
            await index_board(board, sp)

    from operate_within_app_context import operate_within_app_context
    await operate_within_app_context(index_boards)


if __name__ == "__main__":
    import sys
    run(main(sys.argv[1:]))
