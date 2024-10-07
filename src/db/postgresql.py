import asyncpg

from configs import db_conf

from .base_db import BasePlaceHolderGen

sql_echo = db_conf.get('echo', False)
postgresql_conf = db_conf.get('postgresql', {})

async def _get_pool(store=True):
    # we apply an attribute on this function to avoid polluting the module's namespace
    if not hasattr(_get_pool, 'pool') or not store:
        pool = await asyncpg.create_pool(
            **postgresql_conf,
            autocommit=True,
        )
        if not store:
            return pool
        _get_pool.pool = pool
    return _get_pool.pool


async def _run_query_fast(query: str, params: tuple=None):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(query, params)
        return await conn.fetchall()

async def _run_query_dict(query: str, params=None, commit=False):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        if sql_echo:
            print('::SQL::', query)
            print('::PARAMS::', query)

        await conn.execute(query, params)

        if commit:
            return conn.commit()

        return await conn.fetchall()


async def _close_pool():
    if not hasattr(_get_pool, 'pool'):
        return
    await _get_pool.pool.close()
    del _get_pool.pool


class PostgresqlPlaceholderGen(BasePlaceHolderGen):
    __slots__ = ('counter')

    def __init__(self):
        self.counter = 0
    
    def __call__(self):
        self.counter += 1
        return f':{self.counter}'

PlaceHolderGenerator = PostgresqlPlaceholderGen