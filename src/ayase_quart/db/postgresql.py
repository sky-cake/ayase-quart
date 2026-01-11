import asyncpg

from .base_db import BasePlaceHolderGen, BasePoolManager, BaseQueryRunner


class PostgresqlPoolManager(BasePoolManager):
    def __init__(self, postgresql_conf=None):
        self.postgresql_conf = postgresql_conf or {}
        self.pool = None


    async def get_pool(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(**self.postgresql_conf)
        return self.pool


    async def close_pool(self):
        if self.pool is None:
            return

        await self.pool.close()
        self.pool = None


class PostgresqlQueryRunner(BaseQueryRunner):
    def __init__(self, pool_manager: PostgresqlPoolManager, sql_echo=False):
        self.pool_manager = pool_manager
        self.sql_echo = sql_echo


    async def run_query(self, query: str, params=None, commit=False, **kwargs):
        """kwargs to soak up `dict_row`"""
        pool = await self.pool_manager.get_pool()

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


    async def run_query_fast(self, query: str, params=None):
        return await self.run_query(query, params, dict_row=False)


    async def run_script(self, query: str):
        return await self.run_query_fast(query)


class PostgresqlPlaceholderGen(BasePlaceHolderGen):
    __slots__ = ('counter',)

    def __init__(self, start: int=0):
        self.counter = start

    def __call__(self):
        self.counter += 1
        return f':{self.counter}'
