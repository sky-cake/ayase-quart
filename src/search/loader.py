from collections import defaultdict
from itertools import batched
from typing import Callable
from concurrent.futures import ProcessPoolExecutor as Executor
# from multiprocessing import Manager, Queue as Queue_p
from asyncio import (
    Queue as Queue_a,
    CancelledError,
    gather,
    create_task,
    wrap_future,
)

from tqdm.asyncio import tqdm as tqdm_a
from tqdm import tqdm

from asagi_converter import get_selector, get_text_quotelinks

from .providers.baseprovider import BaseSearch
from .providers import search_index_fields
from .post_metadata import pack_metadata, board_2_int, board_int_num_2_pk
from posts.capcodes import capcode_2_id
from db import query_tuple, prime_db_pool, close_db_pool

'''
Hard to find the sweetspot for THREAD_BATCH, goldilocks zone is anywhere between 20-100, also it affects everything downchain
Pros for higher value:
    less random IO and more raw disk throughput
    less async synchronization overhead.
Pros for lower value:
    better mysql index hits
    less batch size variability
    smaller query size for mysql to parse
'''
THREAD_BATCH = 80 

THREAD_BATCH_MULT = 20 # this calculation is wrong, should depend on THREAD_BATCH and the optimal thread select size
POST_BATCH = 5_000 # currently fitted for meili & lnx
EXTRACT_TASKS = 8 # if THREAD_BATCH is lower, increase, if its higher, decrease. modify THREAD_BATCH first, then try to find optimum.
TRANSFORM_TASKS = 6 # Have just enough to keep the row_batch_q always low, competes for cpu with the search engine
EXEC_PROCESSES = TRANSFORM_TASKS + 1 # always keep an extra around in case one of them hiccups
INSERT_TASKS = 5 # minimize to keep async event loop compact while keeping the post_batch_q low, max is how many write threads lnx has
ROWS_BATCH_Q_MAX_DEPTH = TRANSFORM_TASKS * 15 # this calculation is wrong, depend on POST_BATCH as well
POST_BATCH_Q_MAX_DEPTH = INSERT_TASKS * 20 # also wrong for the same reasons ^
BAR_INTERVAL = 0.2 # tqdm refresh rate, 0.25 and 0.3 provided no extra speedups

'''
Big pipeline
threads_worker
    mysql bound
        only 1 instance needed
    loads threads in batches into the thread_nums queue
extract_tasks
    mysql bound
        only 2-3 instance needed
    pulls a block of threads from the thread_nums queue
    selects posts in thread_nums as quickly as possible
        no AttrDicts here, otherwise turning rows of tuples to dicts blocks the async runtime
    drops the rows into the rows_batch queue
transform_tasks
    cpu bound
        as many instances as possible to ensure the rows_batch queue is never full
        don't add any hidden IO to it, the whole thing gets sent to another process
    pulls a batch of rows (list of tuples) from the rows_batch queue
    drops it into the multiprocessing process pool with the correct function and params
    awaits for the result (bytes)
    drops the results into the post_batch queue
insert_tasks
    search engine bound
        as many instances as possible to ensure the rows_batch queue is never full
    pulls some bytes from the post_batch queue
    shoves them into the search engine

wait for things to complete from the top down
    first the threads_worker
    then the queue it populates

    then the extract_tasks
    then the queue those populate

    then the transform_tasks
    then the queue those populate

    finally the insert_tasks
'''

class BoardLoaderPipeline:
    board: str # short
    search_provider: BaseSearch
    thread_num_q: Queue_a
    rows_batch_q: Queue_a
    post_batch_q: Queue_a
    thread_nums_p: tqdm # this progress bar is a normal progress bar of batches of thread_nums. The total keeps going up until the the thread worker can't find anymore thread_nums.
    rows_batch_p: tqdm # this progress bar is a queue of batches of sql rows
    posts_batch_p: tqdm # this progress bar is a queue of batches of processed posts as bytes, ready to be shipped out
    posts_total_p: tqdm # this progress bar is used to show the total progress of posts and the ingestion rate
    process_pool: Executor

    def __init__(self, board: str, search_provider: BaseSearch):
        self.board = board
        self.search_provider = search_provider

    async def run(self):
        wait_pool = prime_db_pool()
        self.process_pool = Executor(max_workers=EXEC_PROCESSES)
        await wait_pool
        try:
            await self._run()
        except Exception as e:
            raise e
        finally:
            wait_http_sql = gather(
                self.search_provider.close(),
                close_db_pool(),
            )
            self.close()
            await wait_http_sql

    # we should probably put all the tasks as members so we can shut them down on exception
    async def _run(self):
        self.thread_num_q = Queue_a() # can take all the thread_nums with no risk
        self.rows_batch_q = Queue_a(ROWS_BATCH_Q_MAX_DEPTH) # Capped so the memory of the python process doesn't grow out of bounds
        self.post_batch_q = Queue_a(POST_BATCH_Q_MAX_DEPTH) # Capped for same ^

        # start filling the thread_queue, only 1 awaitable needed
        wait_threads = self.threads_worker()

        # create tasks from extract workers
        extract_tasks = [
            create_task(self.extract_worker())
            for _ in range(EXTRACT_TASKS)
        ]

        # create tasks from transform workers
        transform_tasks = [
            create_task(self.transform_worker())
            for _ in range(TRANSFORM_TASKS)
        ]

        self.setup_progress_bars()

        # create tasks from insert workers
        insert_tasks = [
            create_task(self.insert_worker())
            for _ in range(INSERT_TASKS)
        ]

        # first wait for thread worker to complete filling thread_nums queue
        await wait_threads

        # then wait for the extract workers to finish consuming the thread_nums queue
        await self.thread_num_q.join()
        # we can now kill the extract tasks
        for task in extract_tasks:
            task.cancel()
        await gather(*extract_tasks)

        # then wait for the transform workers to finish consuming the rows_batch queue
        await self.rows_batch_q.join()
        # we can now kill the transform tasks
        for task in transform_tasks:
            task.cancel()
        await gather(*transform_tasks)

        # finally wait for insert workers to finish pushing batches of posts into the search engine
        await self.post_batch_q.join()
        # we can now kill the insert tasks
        for task in insert_tasks:
            task.cancel()
        await gather(*insert_tasks)

    async def threads_worker(self):
        total = 0
        async for thread_nums in tqdm_a(get_board_threads(self.board), desc='get thread_nums', leave=False):
            for batch in batched(thread_nums, THREAD_BATCH):
                self.thread_num_q.put_nowait(batch)
                total += 1
            self.thread_nums_p.total = total
            self.thread_nums_p.refresh()

    async def extract_worker(self):
        board = self.board
        while True:
            try:
                thread_nums = await self.thread_num_q.get()
            except CancelledError:
                break
            pf_rows = await get_post_rows(board, thread_nums)
            await self.rows_batch_q.put(pf_rows)
            self.thread_num_q.task_done()
            self.thread_nums_p.update()
            self.rows_batch_p.update()

    async def transform_worker(self):
        board = self.board
        # mp_man = Manager()
        # mp_container = mp_man.list()
        post_pack_fn = self.search_provider.get_post_pack_fn()
        batch_pack_fn = self.search_provider.get_batch_pack_fn()
        while True:
            try:
                rows = await self.rows_batch_q.get()
            except CancelledError:
                break
            post_byte_batches = await wrap_future(self.process_pool.submit(process_post_rows, board, rows, post_pack_fn, batch_pack_fn))
            # mp_container.append(rows)
            # post_byte_batches = await wrap_future(self.process_pool.submit(process_post_rows, board, mp_container, post_pack_fn, batch_pack_fn))
            # mp_container.pop()
            for post_bytes in post_byte_batches:
                await self.post_batch_q.put(post_bytes)
                self.posts_batch_p.update()
            self.rows_batch_q.task_done()
            self.rows_batch_p.update(-1)

    async def insert_worker(self):
        while True:
            try:
                qty, post_batch = await self.post_batch_q.get()
            except CancelledError:
                break
            await self.search_provider.add_posts_bytes(post_batch)
            self.post_batch_q.task_done()
            self.posts_total_p.update(qty)
            self.posts_batch_p.update(-1)

    def setup_progress_bars(self):
        self.thread_nums_p = tqdm(desc=f'thread_nums {THREAD_BATCH}', initial=0, unit=f' b', mininterval=BAR_INTERVAL)
        self.rows_batch_p = tqdm(desc=f'rows queue {THREAD_BATCH}', initial=0, total=ROWS_BATCH_Q_MAX_DEPTH, unit=f' b', mininterval=BAR_INTERVAL)
        self.posts_batch_p = tqdm(desc=f'posts queue {POST_BATCH}', initial=0, total=POST_BATCH_Q_MAX_DEPTH, unit=f' b', mininterval=BAR_INTERVAL)
        self.posts_total_p = tqdm(desc='posts indexed', initial=0, unit=' posts', mininterval=BAR_INTERVAL)
    
    def close(self):
        self.process_pool.shutdown()
        self.thread_nums_p.close()
        self.posts_batch_p.close()
        self.posts_total_p.close()

async def index_board(board: str, search_provider: BaseSearch):
    board_loader = BoardLoaderPipeline(board, search_provider)
    await board_loader.run()

# these are get_selector() columns + whatever is added in get_post_rows()
row_keys = ('thread_num', 'no', 'board_shortname', 'now', 'deleted_time', 'name', 'sticky', 'sub', 'w', 'h', 'tn_w', 'tn_h', 'time', 'asagi_preview_filename', 'asagi_filename', 'tim', 'md5', 'fsize', 'filename', 'ext', 'resto', 'capcode', 'trip', 'spoiler', 'country', 'poster_hash', 'closed', 'filedeleted', 'exif', 'com', 'doc_id', 'title', 'timestamp')
# can be a bit more lenient in regargs to efficiency, we're farming this out to multiprocessing
def process_post_rows(board: str, rows: list[tuple], post_pack_fn: Callable[[dict], dict], byte_pack_fn: Callable[[list[dict]], bytes]):
    # the board_int is the same for all the posts
    board_int = board_2_int(board)

    # recreate the dicts here, since we're in a whole other process
    rows = [{k:v for k,v in zip(row_keys, row)} for row in rows]

    # the rows contain all posts within a batch of threads of a single board, so we're guaranteed to find all the replies
    reply_lookup = get_reply_lookup(rows)

    # generator, because it'll get pulled by the batching anyways
    posts = (process_post(row, board_int, reply_lookup, post_pack_fn) for row in rows)
    
    # do more work while we're in another process

    # pack the posts into binary data, ready to be shipped to a search engine, batched by POST_BATCH
    # this way the async main thread doesn't have to process dicts or do json encoding
    # we must keep the length of the batch because the batch is now just a pile of bytes
    batches = [(len(batch), byte_pack_fn(batch)) for batch in batched(posts, POST_BATCH)]
    return batches

# factored out logic for processing single post
def process_post(post: dict, board_int: int, thread_replies: dict, post_pack_fn: Callable[[dict], dict]) -> dict:
    post['replies'] = thread_replies.get(post['no'], []) # need replies before packing metadata
    post['capcode'] = capcode_2_id(post['capcode']) # cast the capcode to int also in the metadata
    post['data'] = pack_metadata(post)
    post['pk'] = board_int_num_2_pk(board_int, post["doc_id"])
    post['board'] = board_int
    post['op'] = post['resto'] == 0
    rename_keys(post)
    set_bool_fields(post)
    remove_fields(post)
    return post_pack_fn(post)

key_remap = (
    ('deleted', 'filedeleted'),
    ('comment', 'com'),
    ('media_filename', 'filename'),
    ('media_hash', 'md5'),
    ('num', 'no'),
    ('width', 'w'),
    ('height', 'h'),
)
def rename_keys(post: dict):
    for se_key, asagi_key in key_remap:
        post[se_key] = post.pop(asagi_key)

# mysql bool is just tinyint
bool_fields = tuple(f.field for f in search_index_fields if f.field_type is bool)
def set_bool_fields(post: dict):
    for field in bool_fields:
        post[field] = bool(post[field])

keep_fields_pop = {f.field for f in search_index_fields}
def remove_fields_pop(post: dict):
    '''removes fields not indexed by the search engine'''
    remove_fields = post.keys() - keep_fields_pop
    for f in remove_fields:
        del post[f]

keep_fields_new_dict = tuple(f.field for f in search_index_fields)
def remove_fields_new_dict(post: dict):
    post = {k: post[k] for k in keep_fields_new_dict}

# pop is forced to iterate a bit more but new_dict is forced to allocate a new dict entirely
remove_fields = remove_fields_pop

def get_reply_lookup(rows: list[dict]):
    replies = defaultdict(list)
    for row in rows:
        if not (comment := row.get('com')):
            continue
        num = row['no']
        for quotelink in get_text_quotelinks(comment):
            replies[int(quotelink)].append(num)
    return replies


max_placeholders = ','.join('%s' for _ in range(THREAD_BATCH))
async def get_post_rows(board: str, thread_nums: list[int]):
    # placeholders = ','.join(['%s'] * len(thread_nums))  # we do this because, "sqlite3.ProgrammingError: Error binding parameter 1: type 'tuple' is not supported"

    # don't rebuild the placeholders when they will always be the same except the last one
    placeholders = max_placeholders if len(thread_nums) == THREAD_BATCH else ','.join(['%s'] * len(thread_nums))

    # the query generated by get_selector(board) is now the bottleneck
    q = f'''
    {get_selector(board)},
    `doc_id`, `title`, `timestamp`
    from `{board}`
    where thread_num in ({placeholders})
    ;'''
    return await query_tuple(q, thread_nums)

# we need a "from" parameter, to only index threads newer than a certain thread
async def get_board_threads(board: str):
    next_batch = lambda after: f'thread_num > {after}'
    after = 0
    batch_size = THREAD_BATCH * THREAD_BATCH_MULT
    while True:
        q = f"SELECT thread_num FROM {board}_threads where {next_batch(after)} order by thread_num asc limit {batch_size};"
        rows = await query_tuple(q)
        if not rows:
            break
        yield [row[0] for row in rows]
        if len(rows) < batch_size:
            break

        after = rows[-1][0]


async def main(boards):
    from .providers import get_search_provider

    sp = get_search_provider()
    try:
        for board in boards:
            await index_board(board, sp)
    except Exception as e:
        print(e)
    finally:
        await gather(
            sp.close(),
            close_db_pool(),
        )