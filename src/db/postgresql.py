import asyncpg
from quart import current_app

from configs import CONSTS

from .db_interface import DatabaseInterface


class PostgreSQLDatabaseAppContext(DatabaseInterface):
    async def connect(self):
        current_app.pool = await _get_pool(store=False)
        print('Postgresql pool open')

    async def query_execute(self, sql: str, params=None, fetchone=False, commit=False):
        async with current_app.pool.acquire() as conn:
            if CONSTS.sql_echo:
                print('::SQL::', sql)

            await conn.execute(sql, params)

            if commit:
                return conn.commit()

            if fetchone:
                return await conn.fetchone()
            return await conn.fetchall()

    async def disconnect(self):
        await current_app.pool.close()


# Functions below are for doing Tuple queries, which are faster fetching Dict results
async def _get_pool(store=True):
    # we apply an attribute on this function to avoid polluting the module's namespace
    if not hasattr(_get_pool, 'pool') or not store:
        pool = await asyncpg.create_pool(
            host=CONSTS.db_host,
            port=CONSTS.db_port,
            user=CONSTS.db_user,
            password=CONSTS.db_password,
            database=CONSTS.db_database,
            min_size=CONSTS.db_min_connections,
            max_size=CONSTS.db_max_connections,
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


async def _close_pool():
    if not hasattr(_get_pool, 'pool'):
        return
    await _get_pool.pool.close()
    delattr(_get_pool, 'pool')


DatabaseAppContext = PostgreSQLDatabaseAppContext