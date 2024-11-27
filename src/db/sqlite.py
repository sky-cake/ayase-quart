import aiosqlite

from .base_db import BasePlaceHolderGen, BasePoolManager, BaseQueryRunner


class DotDict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class SqlitePoolManager(BasePoolManager):
    def __init__(self, sqlite_conf=None, sql_echo=False):
        self.sqlite_conf = sqlite_conf or {}
        self.sql_echo = sql_echo
        self.pools = {}

    def row_factory(self, cursor, row: tuple):
        keys = [col[0] for col in cursor.description]
        return DotDict({k: v for k, v in zip(keys, row)})

    async def create_pool(self, identifier='id1', dict_row=False):
        pool = await aiosqlite.connect(self.sqlite_conf['database'])

        pool.row_factory = self.row_factory if dict_row else None

        self.pools[identifier] = pool
        return pool

    async def get_pool(self, identifier='id1', store=True, dict_row=False):
        if not store:
            return await self.create_pool(identifier, dict_row=dict_row)

        if identifier in self.pools:
            # assuming this is cheap to toggle
            # we avoid having to juggle identifier codes this way
            # still get to have multiple pools for asagi, moderation, etc. if we want
            self.pools[identifier].row_factory = self.row_factory if dict_row else None
            return self.pools[identifier]

        return await self.create_pool(identifier, dict_row=dict_row)

    async def close_pool(self, identifier='id1'):
        if pool := self.pools.pop(identifier, None):
            await pool.close()

    async def close_all_pools(self):
        for pool in self.pools.values():
            await pool.close()
        self.pools.clear()


class SqliteQueryRunner(BaseQueryRunner):
    def __init__(self, pool_manager: SqlitePoolManager, sql_echo=False):
        self.pool_manager = pool_manager
        self.sql_echo = sql_echo

    async def run_query(self, query: str, params=None, commit=False, identifier='id1', dict_row=True):
        pool = await self.pool_manager.get_pool(identifier, dict_row=dict_row)

        if self.sql_echo:
            print('::SQL::', query)
            print('::PARAMS::', params)

        async with pool.execute(query, params) as cursor:
            if commit:
                await pool.commit()
                return
            return await cursor.fetchall()

    async def run_query_fast(self, query: str, params=None, identifier='id1'):
        return await self.run_query(query, params, identifier=identifier, dict_row=False)


class SqlitePlaceholderGen(BasePlaceHolderGen):
    __slots__ = ()

    def __call__(self):
        return '?'
