import asyncpg

from enums import DbPool

from .base_db import BasePlaceHolderGen, BasePoolManager, BaseQueryRunner


class PostgresqlPoolManager(BasePoolManager):
    def __init__(self, postgresql_conf=None):
        self.postgresql_conf = postgresql_conf or {}
        self.pools = {}

    async def create_pool(self, p_id=DbPool.main, dict_row=False):
        """`dict_row` is a placeholder/vestigial."""
        if p_id in self.pools:
            return self.pools[p_id]

        pool = await asyncpg.create_pool(**self.postgresql_conf)
        self.pools[p_id] = pool
        return pool

    async def get_pool(self, p_id=DbPool.main, store=True, dict_row=False):
        if not store:
            return await asyncpg.create_pool(**self.postgresql_conf)

        if p_id not in self.pools:
            await self.create_pool(p_id, dict_row=dict_row)

        return self.pools[p_id]

    async def close_pool(self, p_id=DbPool.main):
        if p_id in self.pools:
            await self.pools[p_id].close()
            del self.pools[p_id]

    async def close_all_pools(self):
        for p_id in list(self.pools.keys()):
            await self.close_pool(p_id)


class PostgresqlQueryRunner(BaseQueryRunner):
    def __init__(self, pool_manager: PostgresqlPoolManager, sql_echo=False):
        self.pool_manager = pool_manager
        self.sql_echo = sql_echo


    async def run_query(self, query: str, params=None, commit=False, p_id=DbPool.main, dict_row=True):
        pool = await self.pool_manager.get_pool(p_id, dict_row=dict_row)

        async with pool.acquire() as conn:
            if self.sql_echo:
                print('::SQL::', query)
                print('::PARAMS::', params)

            if commit:
                # this will auto-commit
                # https://magicstack.github.io/asyncpg/current/usage.html#transactions
                async with conn.transaction():
                    await conn.execute(query, *params if params else [])
                return

            # Record objects always returned
            # https://magicstack.github.io/asyncpg/current/api/index.html#record-objects
            # if dict_row:
            #     results = await conn.fetch(query, *params if params else [])
            #     return [dict(result) for result in results]
            return await conn.fetch(query, *params if params else [])


    async def run_query_fast(self, query: str, params=None, p_id=DbPool.main):
        return await self.run_query(query, params, p_id=p_id, dict_row=False)
    
    async def run_script(self, query: str, p_id=DbPool.main):
        return await self.run_query_fast(query, p_id=p_id)


class PostgresqlPlaceholderGen(BasePlaceHolderGen):
    __slots__ = ('counter',)

    def __init__(self):
        self.counter = 0

    def __call__(self):
        self.counter += 1
        return f':{self.counter}'
