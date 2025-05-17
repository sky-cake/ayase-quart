from asyncio import CancelledError
from asyncio import Queue as Queue_a
from asyncio import Task, create_task, gather, wrap_future
from concurrent.futures import ProcessPoolExecutor as Executor
from itertools import batched
from typing import AsyncGenerator, Callable, List

from tqdm import tqdm
from tqdm.asyncio import tqdm as tqdm_a

from asagi_converter import get_selector, selector_columns
from db import db_q
from posts.capcodes import capcode_2_id
from posts.quotelinks import get_quotelink_lookup

from .post_metadata import board_2_int, board_int_num_2_pk, pack_metadata
from .providers import search_index_fields
from .providers.baseprovider import BaseSearch

"""
Hard to find the sweetspot for THREAD_BATCH, goldilocks zone is anywhere between 20-100, also it affects everything downchain.

Pros for higher value:
    - less random IO and more raw disk throughput
    - less async synchronization overhead.

Pros for lower value:
    - better mysql index hits
    - less batch size variability
    - smaller query size for mysql to parse
"""
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


async def kill_tasks(tasks: List[Task]):
    for task in tasks:
        task.cancel()
    await gather(*tasks)


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
        wait_pool = db_q.prime_db_pool()
        self.process_pool = Executor(max_workers=EXEC_PROCESSES)
        await wait_pool
        try:
            await self._run()
        except Exception as e:
            raise e
        finally:
            wait_http_sql = gather(db_q.close_db_pool())
            self.close()
            await wait_http_sql

    # Note: we should probably put all the tasks as members so we can shut them down on exception
    async def _run(self):
        self.thread_num_q = Queue_a() # can take all the thread_nums with no risk
        self.rows_batch_q = Queue_a(ROWS_BATCH_Q_MAX_DEPTH) # Capped so the memory of the python process doesn't grow out of bounds
        self.post_batch_q = Queue_a(POST_BATCH_Q_MAX_DEPTH) # Capped so the memory of the python process doesn't grow out of bounds

        wait_threads = self.threads_worker()  # only 1 awaitable needed

        extract_tasks = [create_task(self.extract_worker()) for _ in range(EXTRACT_TASKS)]
        transform_tasks = [create_task(self.transform_worker()) for _ in range(TRANSFORM_TASKS)]
        self.setup_progress_bars()
        insert_tasks = [create_task(self.insert_worker()) for _ in range(INSERT_TASKS)]

        await wait_threads # first wait for thread worker to complete filling thread_nums queue

        await self.thread_num_q.join() # block until all items in the queue have been gotten and processed.

        await kill_tasks(extract_tasks)
        await self.rows_batch_q.join() # wait for the transform workers to finish consuming the rows_batch queue

        await kill_tasks(transform_tasks)
        await self.post_batch_q.join() # wait for insert workers to finish pushing batches of posts into the search engine

        await kill_tasks(insert_tasks)


    async def threads_worker(self):
        """
        MYSQL bound process.

        - Only 1 instance needed
        - Workflow:
            1. Loads threads in batches into the `thread_nums` queue.
        """
        total = 0
        async for thread_nums in tqdm_a(get_board_threads(self.board), desc='get thread_nums', leave=False):
            for batch in batched(thread_nums, THREAD_BATCH):
                self.thread_num_q.put_nowait(batch)
                total += 1
            self.thread_nums_p.total = total
            self.thread_nums_p.refresh()


    async def extract_worker(self):
        """
        MySQL bound process.

        - Only 2-3 instances needed.
        - Workflow:
            1. Pull a block of thread numbers from the `thread_nums` queue.
            2. Select posts for the thread numbers as quickly as possible.
            3. Drop the selected rows into the `rows_batch` queue.
        - Avoid using `AttrDicts` to prevent blocking the async runtime when converting rows of tuples to dicts.
        """
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
        """
        CPU bound process.

        - Run as many instances as possible to ensure the `rows_batch` queue is never full.
        - Workflow:
            1. Pull a batch of rows (list of tuples) from the `rows_batch` queue.
            2. Drop it into the multiprocessing process pool with the appropriate function and parameters.
            3. Await the result (bytes).
        - Place the results into the `post_batch` queue.
        - Avoid any hidden I/O; the entire process is sent to another process.
        """
        board = self.board

        post_pack_fn = self.search_provider.get_post_pack_fn()
        batch_pack_fn = self.search_provider.get_batch_pack_fn()
        while True:
            try:
                rows = await self.rows_batch_q.get()
            except CancelledError:
                break
            post_byte_batches = await wrap_future(self.process_pool.submit(process_post_rows, board, rows, post_pack_fn, batch_pack_fn))

            for post_bytes in post_byte_batches:
                await self.post_batch_q.put(post_bytes)
                self.posts_batch_p.update()
            self.rows_batch_q.task_done()
            self.rows_batch_p.update(-1)


    async def insert_worker(self):
        """
        Search Engine bound process.

        - Run as many instances as possible to ensure the `rows_batch` queue is never full.
        - Workflow:
            1. Pull bytes from the `post_batch` queue.
            2. Insert them into the search engine.
        """
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
        self.thread_nums_p = tqdm(desc=f'thread_nums {THREAD_BATCH}', initial=0, unit=' b', mininterval=BAR_INTERVAL)
        self.rows_batch_p = tqdm(desc=f'rows queue {THREAD_BATCH}', initial=0, total=ROWS_BATCH_Q_MAX_DEPTH, unit=' b', mininterval=BAR_INTERVAL)
        self.posts_batch_p = tqdm(desc=f'posts queue {POST_BATCH}', initial=0, total=POST_BATCH_Q_MAX_DEPTH, unit=' b', mininterval=BAR_INTERVAL)
        self.posts_total_p = tqdm(desc='posts indexed', initial=0, unit=' posts', mininterval=BAR_INTERVAL)

    def close(self):
        self.process_pool.shutdown()
        self.thread_nums_p.close()
        self.posts_batch_p.close()
        self.posts_total_p.close()


async def index_board(board: str, search_provider: BaseSearch):
    board_loader = BoardLoaderPipeline(board, search_provider)
    await board_loader.run()


max_placeholders = db_q.phg.qty(THREAD_BATCH)
async def get_post_rows(board: str, thread_nums: list[int]):
    # don't rebuild the placeholders when they will always be the same except the last one
    placeholders = max_placeholders if len(thread_nums) == THREAD_BATCH else db_q.phg.size(thread_nums)

    # you may need to update `row_keys` (below) if you modify this query's selectors.
    # file_archived = 1/true when there is no media associate with post cus we still want to have it in results
    q = f"""
        {get_selector(board)},
            doc_id,
            title,
            timestamp,
            case when comment is not null then {db_q.length_method}(comment) else 0 end as comment_length,
            case when title is not null then {db_q.length_method}(title) else 0 end as title_length,
            case when `{board}`.media_orig is null then 1 when image.board is not null then 1 else 0 end as file_archived
        from `{board}` left join image on image.board = '{board}' and `{board}`.media_orig is not null and `{board}`.media_orig = image.filename
        where thread_num in ({placeholders})
    ;"""

    # the query generated by get_selector(board) is now the bottleneck
    return await db_q.query_tuple(q, thread_nums)


# these are [get_selector() columns] + [whatever is added in get_post_rows()]
row_keys = selector_columns + ('doc_id', 'title', 'timestamp', 'comment_length', 'title_length', 'file_archived')
# can be a bit more lenient in regargs to efficiency, we're farming this out to multiprocessing
def process_post_rows(board: str, rows: list[tuple], post_pack_fn: Callable[[dict], dict], byte_pack_fn: Callable[[list[dict]], bytes]):
    # the board_int is the same for all the posts
    board_int = board_2_int(board)

    # recreate the dicts here, since we're in a whole other process
    rows = [{k:v for k,v in zip(row_keys, row)} for row in rows]

    # the rows contain all posts within a batch of threads of a single board, so we're guaranteed to find all the replies
    post_2_quotelinks = get_quotelink_lookup(rows)

    # generator, because it'll get pulled by the batching anyways
    posts = (process_post(row, board_int, post_2_quotelinks, post_pack_fn) for row in rows)

    # do more work while we're in another process

    # pack the posts into binary data, ready to be shipped to a search engine, batched by POST_BATCH
    # this way the async main thread doesn't have to process dicts or do json encoding
    # we must keep the length of the batch because the batch is now just a pile of bytes
    batches = [(len(batch), byte_pack_fn(batch)) for batch in batched(posts, POST_BATCH)]
    return batches


def process_post(post: dict, board_int: int, post_2_quotelinks: dict, post_pack_fn: Callable[[dict], dict]) -> dict:
    """Factored out logic for processing single post.
    """
    post['quotelinks'] = post_2_quotelinks.get(post['num'], []) # need replies before packing metadata
    post['capcode'] = capcode_2_id(post['capcode']) # cast the capcode to int also in the metadata
    post['data'] = pack_metadata(post)
    post['pk'] = board_int_num_2_pk(board_int, post["doc_id"])
    post['board'] = board_int

    set_bool_fields(post)
    remove_fields(post)

    return post_pack_fn(post)


# mysql bool is just tinyint
bool_fields = tuple(f.field for f in search_index_fields if f.field_type is bool)
def set_bool_fields(post: dict):
    for field in bool_fields:
        post[field] = bool(post[field])


keep_fields_pop = {f.field for f in search_index_fields}
def remove_fields_pop(post: dict):
    """Removes fields not indexed by the search engine."""
    _remove_fields = post.keys() - keep_fields_pop
    for f in _remove_fields:
        del post[f]


keep_fields_new_dict = tuple(f.field for f in search_index_fields)
def remove_fields_new_dict(post: dict):
    post = {k: post[k] for k in keep_fields_new_dict}

# pop is forced to iterate a bit more but new_dict is forced to allocate a new dict entirely
remove_fields: Callable = remove_fields_pop


def next_batch(n: int):
    return f'thread_num > {int(n)}'


async def get_board_threads(board: str, after_thread_num: int=0) -> AsyncGenerator:
    batch_size = THREAD_BATCH * THREAD_BATCH_MULT

    while True:
        q = f"SELECT thread_num FROM `{board}` where op=1 and {next_batch(after_thread_num)} order by thread_num asc limit {batch_size};"
        rows = await db_q.query_tuple(q)
        if not rows:
            break

        yield [row[0] for row in rows]
        if len(rows) < batch_size:
            break

        after_thread_num = rows[-1][0] # thread_num


async def main(boards: list[str], reset: bool=False):
    from .providers import get_index_search_provider

    sp = get_index_search_provider()
    try:
        if reset:
            try:
                await sp.posts_wipe()
            except Exception:
                print('No existing index.')

            await sp.init_indexes()

        for board in boards:
            await index_board(board, sp)
        await sp.finalize()
    except Exception as e:
        print(e)
    finally:
        await gather(
            sp.close(),
            db_q.close_db_pool(),
        )
