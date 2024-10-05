import re

import aiosqlite

from configs import CONSTS





async def _get_pool(store=True):
    # we apply an attribute on this function to avoid polluting the module's namespace
    if not hasattr(_get_pool, 'pool') or not store:
        pool = await aiosqlite.connect(
            CONSTS.db_path,
            autocommit=True,
        )
        if not store:
            return pool
        _get_pool.pool = pool
    return _get_pool.pool


async def _run_query_fast(query: str, params: tuple=None):
    wait_pool = _get_pool()

    # patch query while waiting for the pool to connect on first connection
    query = patch_query(query)

    pool = await wait_pool
    async with pool.execute(query, params) as cursor:
        return await cursor.fetchall()


async def _close_pool():
    if not hasattr(_get_pool, 'pool'):
        return
    await _get_pool.pool.close()
    delattr(_get_pool, 'pool')


re_mysql_bind_to_sqlite_bind = re.compile(r'%\((\w+)\)s')
def patch_query(query: str) -> str:
    """We write queries against MYSQL initially, then apply SQLITE patches with this function."""
    return re_mysql_bind_to_sqlite_bind.sub(r':\1', query).replace('`', '').replace('%s', '?').replace("strftime('?', ", "strftime('%s', ")


