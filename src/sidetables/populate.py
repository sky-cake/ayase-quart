import asyncio
from collections import defaultdict, Counter
from itertools import batched
from typing import AsyncGenerator, Generator, Iterable
from dataclasses import dataclass
from enum import StrEnum

from tqdm import tqdm
from tqdm.asyncio import tqdm as tqdm_a

from db import db_q

BATCH_POSTS = 10000
BATCH_THREADS = 4000
BATCH_IMAGES = 3000

split_tuple =  lambda columns: tuple(columns.split())

post_columns = split_tuple('doc_id num thread_num timestamp media_hash sticky locked')
thread_columns = split_tuple('thread_num time_op time_last time_bump time_last_modified nreplies nimages')
media_columns = split_tuple('media_hash total')

class SideTable(StrEnum):
    threads = 'threads'
    media = 'images'
    users = 'users'
    daily = 'daily'
    deleted = 'deleted'

@dataclass(slots=True)
class Thread:
    replies: int = 0
    images: int = 0
    sticky: int = 0
    locked: int = 0
    time_bump: int = 0
    time_op: int = 0
    time_last: int = 0
    time_last_modified: int = 0

    def get_row(self, thread_num: int) -> tuple[int, ...]:
        return (thread_num, self.time_op, self.time_last, self.time_bump, self.time_last_modified, self.replies, self.images)

# not used
@dataclass(slots=True)
class Media:
    total: int = 0
    banned: int = 0

    def get_row(self, media_hash: int) -> tuple:
        return (media_hash, self.total, self.banned)

def media_row_gen(medias: Counter) -> Generator:
    for batch in batched(medias.items(), BATCH_THREADS):
        yield [(media_hash, count) for media_hash, count in batch]

def thread_row_gen(threads: dict[int, Thread]) -> Generator:
    for batch in batched(threads.items(), BATCH_IMAGES):
        yield [thread.get_row(threadnum) for threadnum, thread in batch]

async def board_rows_gen(board: str, after_doc_id: int=0) -> AsyncGenerator:
    batch_size = BATCH_POSTS

    sql = f"""
    select {','.join(post_columns)}
    from `{board}`
    where doc_id > {db_q.phg()}
    order by doc_id asc
    limit {batch_size}
    ;"""
    while True:
        rows = await db_q.query_tuple(sql, (after_doc_id,))
        if not rows:
            break

        yield rows
        if len(rows) < batch_size:
            break
        after_doc_id = rows[-1][0] # last doc_id

async def insert_sidetable_fresh(sidetable: SideTable, columns: Iterable[str], board: str, rows: list[tuple]):
    ph = ','.join(db_q.phg() for _ in range(len(rows)))
    sql = f'insert into `{board}_{sidetable}`({",".join(columns)}) values {ph};'
    await db_q.query_tuple(sql, (*rows,))

async def aggregate_posts(board: str, after_doc_id: int=0):
    threads = defaultdict(Thread)
    media_hashes = Counter()

    async for row_batch in tqdm_a(board_rows_gen(board, after_doc_id), desc=f'load posts'):
        for _, num, thread_num, timestamp, media_hash, sticky, locked in row_batch:
            thread = threads[thread_num]
            thread.replies += 1
            if media_hash:
                thread.images += 1
                media_hashes[media_hash] += 1

            if timestamp > thread.time_bump:
                thread.time_bump = timestamp
                thread.time_last = timestamp
                thread.time_last_modified = timestamp

            if num == thread_num: # op
                thread.time_op = timestamp
                thread.locked = locked
                thread.sticky = sticky
    
    return threads, media_hashes

async def populate(boards: list[str]):
    if not boards:
        return
    for board in boards:
        print('Populating:', board)

        threads, medias = await aggregate_posts(board)

        for row_batch in tqdm(thread_row_gen(threads), desc=f'insert threads'):
            await insert_sidetable_fresh(SideTable.threads, thread_columns, board, row_batch)
        
        for row_batch in tqdm(media_row_gen(medias), desc=f'insert medias'):
            await insert_sidetable_fresh(SideTable.media, media_columns, board, row_batch)

def run_populate(boards: list[str]):
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(populate(boards))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(db_q.close_db_pool())
        loop.close()
