import aiosqlite

from enums import DbPool

from .base_db import BasePlaceHolderGen, BasePoolManager, BaseQueryRunner


class DotDict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def row_factory(cursor, row: tuple):
    keys = [col[0] for col in cursor.description]
    return DotDict({k: v for k, v in zip(keys, row)})


class SqlitePoolManager(BasePoolManager):
    def __init__(self, sqlite_conf=None, sql_echo=False):
        self.sqlite_conf = sqlite_conf or {}
        self.sql_echo = sql_echo
        self.pools = {}

    async def create_pool(self, p_id=DbPool.main, dict_row=False):
        pool = await aiosqlite.connect(self.sqlite_conf['database'])

        pool.row_factory = row_factory if dict_row else None

        self.pools[p_id] = pool
        return pool

    async def get_pool(self, p_id=DbPool.main, store=True, dict_row=False):
        if not store:
            return await self.create_pool(p_id, dict_row=dict_row)

        if p_id in self.pools:
            # assuming this is cheap to toggle
            # we avoid having to juggle p_id codes this way
            # still get to have multiple pools for asagi, moderation, etc. if we want
            self.pools[p_id].row_factory = row_factory if dict_row else None
            return self.pools[p_id]

        return await self.create_pool(p_id, dict_row=dict_row)

    async def close_pool(self, p_id=DbPool.main):
        if pool := self.pools.pop(p_id, None):
            await pool.close()

    async def close_all_pools(self):
        for pool in self.pools.values():
            await pool.close()
        self.pools.clear()


class SqliteQueryRunner(BaseQueryRunner):
    def __init__(self, pool_manager: SqlitePoolManager, sql_echo=False):
        self.pool_manager = pool_manager
        self.sql_echo = sql_echo

    async def run_query(self, query: str, params=None, commit=False, p_id=DbPool.main, dict_row=True):
        pool = await self.pool_manager.get_pool(p_id, dict_row=dict_row)

        if self.sql_echo:
            print('::SQL::', query)
            print('::PARAMS::', params)

        async with pool.execute(query, params) as cursor:
            results = await cursor.fetchall()

            # commit comes after `fetchall` to support `returing` statements
            if commit:
                await pool.commit()

            return results

    async def run_query_fast(self, query: str, params=None, p_id=DbPool.main):
        return await self.run_query(query, params, p_id=p_id, dict_row=False)


class SqlitePlaceholderGen(BasePlaceHolderGen):
    __slots__ = ()

    def __call__(self):
        return '?'
