import os
from collections import defaultdict, Counter
from functools import cache
from dataclasses import dataclass, field
from itertools import product, batched
from typing import Literal

import aiofiles
from coredis import Redis
from coredis.modules.filters import BloomFilter, CuckooFilter

from configs import mod_conf
from boards import board_shortnames
from db import db_m, db_q
from db.redis import get_redis
from .base_fc import BaseFilterCache

FILTER_INSERT_BATCH = 1000

FC_DEFAULT_DUMP_DIR = '../data/filter_cache/'
FC_DEFAULT_KEY_PREFIX = 'filter_cache:'
FC_DEFAULT_DB = 4

BF_DEFAULT_ERR_RATE = 0.01  # 1% false positive rate
BF_DEFAULT_INIT_SIZE = 8_000_000  # Initial capacity, auto-expands, 8mb -> 1MB/board
BF_DEFAULT_RESIZE_MULT = 2  # Growth factor when capacity reached

CF_DEFAULT_CAPACITY = 10_000
CF_DEFAULT_BUCKET = 1000
CF_DEFAULT_ITER_MAX = 10

mod_r_conf = mod_conf.get('redis', {})
REDIS_FC_DB = mod_r_conf.get('redis_db', FC_DEFAULT_DB)
FC_KEY_PREFIX = mod_r_conf.get('fc_key_prefix', FC_DEFAULT_KEY_PREFIX)
FC_DUMP_DIR = mod_r_conf.get('fc_dump_dir', FC_DEFAULT_DUMP_DIR)

@cache
def fmt_op_count_key(board: str) -> str:
    return f'{FC_KEY_PREFIX}op_count:{board}'

# TODO: move to utils
def u32_to_bytes(val: int) -> bytes:
    return val.to_bytes(4, byteorder='big', signed=False)

@dataclass(unsafe_hash=True, order=True)
class RedisFilter:
    rfilter: BloomFilter|CuckooFilter
    name: Literal['bloom', 'cuckoo'] = field(init=False)
    is_bloom: bool = field(init=False)

    def __post_init__(self):
        self.is_bloom = type(self.rfilter) is BloomFilter
        self.name = 'bloom' if self.is_bloom else 'cuckoo'

    def dump_path(self, board: str) -> str:
        return f'{FC_DUMP_DIR}/{board}_{self.name}.dump'

    @cache
    def fmt_key(self, board: str) -> str:
        return f'{FC_KEY_PREFIX}{self.name}:{board}'

    async def reserve(self, board: str, **kwargs: dict) -> None:
        try:
            await self.rfilter.reserve(self.fmt_key(board), **kwargs)
        except Exception: pass

    async def export_dump(self, board: str) -> None:
        _, board_dump = await self.rfilter.scandump(self.fmt_key(board), 0)
        if not board_dump:
            return
        async with aiofiles.open(self.dump_path(board), 'wb') as f:
            await f.write(board_dump)

    async def import_dump(self, board: str) -> None:
        if not os.path.exists(dump_p := self.dump_path(board)):
            return
        async with aiofiles.open(dump_p, 'rb') as f:
            await self.rfilter.loadchunk(self.fmt_key(board), 0, await f.read())

    async def get_maybe_nums(self, board: str, nums: list[int]) -> list[int]:
        nums_bytes = [u32_to_bytes(num) for num in nums]
        filter_exists = await self.rfilter.mexists(self.fmt_key(board), nums_bytes)
        return [num for num, f_res in zip(nums, filter_exists) if f_res]

    async def add_num(self, board: str, num: int) -> None:
        await self.rfilter.add(self.fmt_key(board), u32_to_bytes(num))

    async def delete_num(self, board: str, num: int) -> None:
        if self.is_bloom:
            return
        await self.rfilter.delete(self.fmt_key(board), u32_to_bytes(num))

    async def bulk_add(self, board: str, nums: list[int]) -> None:
        key = self.fmt_key(board)
        nums_bytes = [u32_to_bytes(num) for num in nums]
        if self.is_bloom:
            await self.rfilter.madd(key, nums_bytes)
        else:
            await self.rfilter.insert(key, nums_bytes)

class FilterCacheRedis(BaseFilterCache):
    def __init__(self, mod_conf: dict):
        super().__init__(mod_conf)
        self.redis: Redis = get_redis(REDIS_FC_DB)
        self.bf = RedisFilter(BloomFilter(client=self.redis))
        self.cf = RedisFilter(CuckooFilter(client=self.redis))

    async def _create_cache(self) -> None:
        for board in board_shortnames:
            await self.bf.reserve(
                board,
                error_rate=mod_r_conf.get('bloom_err_rate', BF_DEFAULT_ERR_RATE),
                capacity=mod_r_conf.get('bloom_init_size', BF_DEFAULT_INIT_SIZE),
                expansion=mod_r_conf.get('bloom_resize_mult', BF_DEFAULT_RESIZE_MULT),
            )
            await self.cf.reserve(
                board,
                capacity=mod_r_conf.get('cuckoo_capacity', CF_DEFAULT_CAPACITY),
                bucketsize=mod_r_conf.get('cuckoo_bucket', CF_DEFAULT_BUCKET),
                maxiterations=mod_r_conf.get('cuckoo_iter_max', CF_DEFAULT_ITER_MAX),
            )
        if not await self._is_cache_populated():
            await self._populate_cache()

    async def _is_cache_populated(self) -> bool:
        if not (keys := await self.redis.keys(f'{FC_KEY_PREFIX}*')):
            return False
        return len(keys) > 0

    async def _populate_cache(self) -> None:
        iter_funcs = [
            self.get_numops_by_board_and_regex_iter,
            self.get_deleted_numops_per_board_iter,
        ]
        board_del_ops = Counter()
        for iter_func in iter_funcs:
            async for board, numops in iter_func():
                board_del_ops[board] += sum(1 for _, op in numops if op == 1)
                await self.bf.bulk_add(board, [num for num, _ in numops])

        async with await self.redis.pipeline(transaction=True) as pipe:
            for board, del_ops in board_del_ops.items():
                pipe.incrby(fmt_op_count_key(board), del_ops)
            await pipe.execute()

        sql = """
        select board_shortname, num
        from report_parent where
            public_access = 'h'
            and mod_status = 'o'
        group by board_shortname, num
        ;"""
        if not (rows := await db_m.query_tuple(sql)):
            return
        board_nums = defaultdict(list)
        for board, num in rows:
            board_nums[board].append(num)
        for board, nums in board_nums.items():
            for batch in batched(nums, FILTER_INSERT_BATCH):
                await self.cf.bulk_add(board, batch)

    async def export_dump(self) -> None:
        for board, rfilter in product(board_shortnames, (self.bf, self.cf)):
            try: await rfilter.export_dump(board)
            except: pass

    async def import_dump(self) -> None:
        for board, rfilter in product(board_shortnames, (self.bf, self.cf)):
            try: await rfilter.import_dump(board)
            except: pass

    async def _teardown(self) -> None:
        if keys := await self.redis.keys(f'{self.FC_PREFIX}*'):
            await self.redis.delete(*keys)

    async def get_op_thread_removed_count(self, board: str) -> int:
        if count := await self.redis.get(fmt_op_count_key(board)):
            return int(count.decode())
        return 0

    # TODO: need to thread in hide_deleted, hide_reported and hide_reported_after_n
    async def get_board_num_pairs(self, posts: list[dict], hide_deleted: bool=True, hide_reported: bool=False) -> set[tuple[str, int]]:
        if not posts or not (hide_deleted or hide_reported):
            return set()
        board_nums = defaultdict(list)
        for post in posts:
            board_nums[post['board_shortname']].append(post['num'])

        board_num_pairs = set()
        for board, nums in board_nums.items():
            if hide_deleted:
                board_num_pairs |= await self.get_deleted(board, nums)
            if hide_reported:
                board_num_pairs |= await self.get_reported(board, nums)
        return board_num_pairs

    async def get_deleted(self, board: str, nums: list[int]) -> set[tuple[str, int]]:
        if not (maybe_nums := await self.bf.get_maybe_nums(board, nums)):
            return set()
        sql = f'select num from `{board}` where deleted = 1 and num in ({db_q.Phg().qty(len(maybe_nums))});'
        return {
            (board, row[0]) for row in
            await db_q.query_tuple(sql, (*maybe_nums,))
        }

    async def get_reported(self, board: str, nums: list[int]) -> set[tuple[str, int]]:
        if not (maybe_nums := await self.cf.get_maybe_nums(board, nums)):
            return set()
        phg = db_m.Phg()
        sql = f"""
        select num from report_parent where
            board = {phg()}
            and public_access = 'h'
            and mod_status = 'o'
            and num in ({phg.qty(len(maybe_nums))})
        ;"""
        return {
            (board, row[0]) for row in
            await db_m.query_tuple(sql, (*maybe_nums,))
        }

    async def _insert_reported_num(self, board: str, num: int) -> None:
        await self.cf.add_num(board, num)

    async def _remove_reported_num(self, board: str, num: int) -> None:
        await self.cf.delete_num(board, num)

    async def _insert_deleted_num(self, board: str, num: int, op: int) -> None:
        return await self.insert_post(board, num, op)

    async def _remove_deleted_num(self, board: str, num: int, op: int) -> None:
        return await self.delete_post(board, num, op)

    async def is_post_removed(self, board: str, num: int) -> bool:
        if await self.get_deleted(board, nums := [num]):
            return True
        return bool(await self.get_reported(board, nums))

    async def insert_post(self, board: str, num: int, op: int) -> None:
        await self.bf.add_num(board, num)
        if op == 1:
            await self.redis.incr(fmt_op_count_key(board))

    async def delete_post(self, board: str, num: int, op: int) -> None:
        # no deleting from bloom filter, rebuild from scratch
        if op == 1:
            await self.redis.decr(fmt_op_count_key(board))
