import asyncpg

from .base_db import BasePlaceHolderGen, BasePoolManager, BaseQueryRunner


class PostgresqlPoolManager(BasePoolManager):
    def __init__(self, postgresql_conf=None):
        self.postgresql_conf = postgresql_conf or {}
        self.pools = {}

    async def create_pool(self, identifier='id1', dict_row=False):
        """`dict_row` is a placeholder/vestigial."""
        if identifier in self.pools:
            return self.pools[identifier]

        pool = await asyncpg.create_pool(**self.postgresql_conf)
        self.pools[identifier] = pool
        return pool

    async def get_pool(self, identifier='id1', store=True, dict_row=False):
        if not store:
            return await asyncpg.create_pool(**self.postgresql_conf)

        if identifier not in self.pools:
            await self.create_pool(identifier, dict_row=dict_row)

        return self.pools[identifier]

    async def close_pool(self, identifier='id1'):
        if identifier in self.pools:
            await self.pools[identifier].close()
            del self.pools[identifier]

    async def close_all_pools(self):
        for identifier in list(self.pools.keys()):
            await self.close_pool(identifier)


class PostgresqlQueryRunner(BaseQueryRunner):
    def __init__(self, pool_manager: PostgresqlPoolManager, sql_echo=False):
        self.pool_manager = pool_manager
        self.sql_echo = sql_echo

    async def run_query(self, query: str, params=None, commit=False, identifier='id1', dict_row=True):
        pool = await self.pool_manager.get_pool(identifier, dict_row=dict_row)

        async with pool.acquire() as conn:
            if self.sql_echo:
                print('::SQL::', query)
                print('::PARAMS::', params)

            if commit:
                # this will auto-commit
                # https://magicstack.github.io/asyncpg/current/usage.html#transactions
                await conn.execute(query, *params if params else [])
                return

            # Record objects always returned
            # https://magicstack.github.io/asyncpg/current/api/index.html#record-objects
            # if dict_row:
            #     results = await conn.fetch(query, *params if params else [])
            #     return [dict(result) for result in results]
            return await conn.fetch(query, *params if params else [])

    async def run_query_fast(self, query: str, params=None, identifier='id1'):
        return await self.run_query(query, params, identifier=identifier, dict_row=False)


class PostgresqlPlaceholderGen(BasePlaceHolderGen):
    __slots__ = ('counter',)

    def __init__(self):
        self.counter = 0

    def __call__(self):
        self.counter += 1
        return f':{self.counter}'
