from abc import ABC, abstractmethod

from aiosqlite import Connection

from asagi_converter import (
    get_deleted_numops_by_board,
    get_numops_by_board_and_regex
)
from boards import board_shortnames
from db import db_m
from enums import DbPool
from utils import make_src_path, read_file
import re


class BaseFilterCache(ABC):
    def __init__(self, mod_conf: dict):
        self.enabled = mod_conf['enabled']
        self.remove_replies_to_hidden_op = mod_conf['remove_replies_to_hidden_op']
        self.regex_filter = mod_conf['regex_filter']
        self.hide_4chan_deleted_posts = mod_conf['hide_4chan_deleted_posts']

        super().__init__()

    async def init(self):
        if not self.enabled:
            return

        await self._create_cache()

    async def get_deleted_numops_per_board_iter(self):
        """Returns a tuple[str, tuple[int, int]]

        `(board, [(num, op), ...])`
        """
        if not (self.hide_4chan_deleted_posts and board_shortnames):
            return
        for board in board_shortnames:
            numops = await get_deleted_numops_by_board(board)
            yield board, numops

    async def get_numops_by_board_and_regex_iter(self):
        """Returns a tuple[str, tuple[int, int]]

        `(board, [(num, op), ...])`
        """
        if not (self.regex_filter and board_shortnames):
            return
        for board in board_shortnames:
            numops = await get_numops_by_board_and_regex(board, self.regex_filter)
            yield board, numops

    @abstractmethod
    async def _create_cache(self) -> None:
        """Create the db schema, filter in redis, whatever"""
        raise NotImplementedError()

    @abstractmethod
    async def _is_cache_populated(self) -> bool:
        """Check if the population routine must be ran"""
        raise NotImplementedError()

    @abstractmethod
    async def _populate_cache(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _teardown(self) -> None:
        """Remove all inserts"""
        raise NotImplementedError()

    @abstractmethod
    async def is_post_removed(self, board: str, num: int) -> bool:
        """Is the post removed?"""
        raise NotImplementedError()

    @abstractmethod
    async def get_op_thread_removed_count(self, board: str) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def insert_post(self, board: str, num: int, op: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def delete_post(self, board: str, num: int, op: int) -> None:
        raise NotImplementedError()

    async def get_board_num_pairs(self, posts: list) -> set[tuple[str, int]]:
        """`set[('g', 12345), ('x', 6789), ...]`"""
        raise NotImplementedError()

    def should_filter(self, board_num_pairs: set, post: dict) -> bool:
        return (
            (self.remove_replies_to_hidden_op and (post['board_shortname'], post['thread_num']) in board_num_pairs)
            or
            ((post['board_shortname'], post['num']) in board_num_pairs)
            or
            (self.hide_4chan_deleted_posts and post['deleted'])
            or
            (self.regex_filter and re.search(self.regex_filter, post['comment'], re.IGNORECASE))
        )

    async def filter_reported_posts(self, posts: list[dict], is_authority: bool=False) -> list:
        if not self.enabled:
            return posts

        if not posts:
            return posts

        board_num_pairs = await self.get_board_num_pairs(posts)

        note = 'Only visible to AQ staff.'

        if is_authority:
            posts = [
                post
                if not self.should_filter(board_num_pairs, post)
                else post | dict(deleted=note)
                for post in posts
            ]
            return posts

        posts = [
            post
            for post in posts
            if not self.should_filter(board_num_pairs, post)
        ]
        return posts


class FilterCacheSqlite(BaseFilterCache):
    """Uses a single table in the moderation sqlite database."""

    def __init__(self, mod_conf: dict):
        super().__init__(mod_conf)


    async def _create_cache(self) -> None:
        moderation_scripts = ["board_nums_cache.sql"]
        for script in moderation_scripts:
            sql_statements = read_file(make_src_path("moderation", "sql", script)).split(";")
            for sql in sql_statements:
                sql += ";"
                await db_m.query_dict(sql, p_id=DbPool.mod, commit=True)


    async def _is_cache_populated(self) -> bool:
        bn_count = await db_m.query_tuple("select count(*) from board_nums_cache", p_id=DbPool.mod)
        return bool(bn_count[0][0])


    async def _populate_cache(self) -> None:
        """
        This isn't needed if we filter posts via python.
        That would be better than creating another data set to track and query, especially for larger data sets.
        It's also better than adding extra filters (is deleted, and regexes) in our database queries.
        We will populate our cache with reported posts only.
        """
        pool: Connection = await db_m.pool_manager.get_pool(p_id=DbPool.mod)
        iter_funcs = [
            self.get_numops_by_board_and_regex_iter,
            self.get_deleted_numops_per_board_iter,
        ]
        for iter_func in iter_funcs:
            async for board_and_numops in iter_func():
                if not (board_and_numops and board_and_numops[1]):
                    continue

                params = [(board_and_numops[0], numop[0], numop[1]) for numop in board_and_numops[1]]
                await pool.executemany("insert or ignore into board_nums_cache (board_shortname, num, op) values (?, ?, ?)", params)
                await pool.commit()

            rows = await db_m.query_tuple("select board_shortname, op, group_concat(distinct num) as nums from report_parent group by board_shortname, op", p_id=DbPool.mod)
            await pool.executemany("insert or ignore into board_nums_cache (board_shortname, op, num) values (?, ?, ?)", rows)
            await pool.commit()


    async def _teardown(self):
        sql = """delete from board_nums_cache"""
        pool: Connection = await db_m.pool_manager.get_pool(p_id=DbPool.mod)
        await pool.execute(sql)
        await pool.commit()


    async def get_op_thread_removed_count(self, board: str) -> int:
        if not self.enabled:
            return 0

        rows = await db_m.query_tuple(f'select count(*) from board_nums_cache where board_shortname = {db_m.phg()} and op = 1', params=[board])
        return rows[0][0]


    async def get_board_num_pairs(self, posts: list) -> set[tuple[str, int]]:
        board_and_nums = [(p['board_shortname'], p['num']) for p in posts]

        ph = ','.join([f'({db_m.phg()},{db_m.phg()})'] * len(board_and_nums))

        expanded = [item for bn in board_and_nums for item in bn]

        sql = f"""
            select board_shortname, num
            from board_nums_cache
            where (board_shortname, num) in ({ph})
        """
        rows = await db_m.query_tuple(sql, expanded)

        return {(row[0], row[1]) for row in rows}


    async def is_post_removed(self, board: str, num: int) -> bool:
        ph = db_m.phg()
        sql = f"""select num from board_nums_cache where board_shortname = {ph} and num = {ph}"""
        row = await db_m.query_tuple(sql, params=[board, num])
        if not row:
            return False
        return True


    async def insert_post(self, board: str, num: int, op: int):
        ph = db_m.phg()
        await db_m.query_dict(
            f"insert or ignore into board_nums_cache (board_shortname, num, op) values ({ph},{ph},{ph})",
            params=[board, num, op],
            commit=True,
        )


    async def delete_post(self, board: str, num: int, op: int):
        ph = db_m.phg()
        await db_m.query_dict(
            f"delete from board_nums_cache where board_shortname = {ph} and num = {ph} and op = {ph}",
            params=[board, num, op],
            commit=True,
        )


def get_filter_cache(mod_conf: dict) -> BaseFilterCache:
    filter_cache_type = mod_conf['filter_cache_type']
    match filter_cache_type:
        case "sqlite":
            return FilterCacheSqlite(mod_conf)
        case _:
            raise NotImplementedError(f"Unsupported filter cache type: {filter_cache_type}")
