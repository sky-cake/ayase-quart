from aiosqlite import Connection

from db import db_m
from utils import make_src_path, read_file
from .base_fc import BaseFilterCache

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
                await db_m.query_dict(sql, commit=True)


    async def _is_cache_populated(self) -> bool:
        bn_count = await db_m.query_tuple("select count(*) from board_nums_cache")
        return bool(bn_count[0][0])


    async def _populate_cache(self) -> None:
        """
        This isn't needed if we filter posts via python.
        That would be better than creating another data set to track and query, especially for larger data sets.
        It's also better than adding extra filters (is deleted, and regexes) in our database queries.
        We will populate our cache with reported posts only.
        """
        pool: Connection = await db_m.pool_manager.get_pool()
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

            rows = await db_m.query_tuple("select board_shortname, op, group_concat(distinct num) as nums from report_parent group by board_shortname, op")
            await pool.executemany("insert or ignore into board_nums_cache (board_shortname, op, num) values (?, ?, ?)", rows)
            await pool.commit()


    async def _teardown(self):
        sql = """delete from board_nums_cache"""
        pool: Connection = await db_m.pool_manager.get_pool()
        await pool.execute(sql)
        await pool.commit()


    async def get_op_thread_removed_count(self, board: str) -> int:
        rows = await db_m.query_tuple(f'select count(*) from board_nums_cache where board_shortname = {db_m.Phg()()} and op = 1', params=[board])
        return rows[0][0]


    async def get_board_num_pairs(self, posts: list) -> set[tuple[str, int]]:
        board_and_nums = [(p['board_shortname'], p['num']) for p in posts]

        phg = db_m.Phg()
        ph = ','.join(f'({phg()},{phg()})' for _ in range(len(board_and_nums)))

        expanded = [item for bn in board_and_nums for item in bn]

        sql = f"""
            select board_shortname, num
            from board_nums_cache
            where (board_shortname, num) in ({ph})
        """
        rows = await db_m.query_tuple(sql, expanded)

        return {(row[0], row[1]) for row in rows}


    async def is_post_removed(self, board: str, num: int) -> bool:
        phg = db_m.Phg()
        sql = f"""select num from board_nums_cache where board_shortname = {phg()} and num = {phg()}"""
        row = await db_m.query_tuple(sql, params=[board, num])
        if not row:
            return False
        return True


    async def insert_post(self, board: str, num: int, op: int):
        phg = db_m.Phg()
        await db_m.query_dict(
            f"insert or ignore into board_nums_cache (board_shortname, num, op) values ({phg()},{phg()},{phg()})",
            params=[board, num, op],
            commit=True,
        )


    async def delete_post(self, board: str, num: int, op: int):
        phg = db_m.Phg()
        await db_m.query_dict(
            f"delete from board_nums_cache where board_shortname = {phg()} and num = {phg()} and op = {phg()}",
            params=[board, num, op],
            commit=True,
        )

