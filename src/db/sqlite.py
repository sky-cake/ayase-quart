import re
import asyncio

import aiosqlite

from configs import CONSTS
from .base_db import BasePlaceHolderGen


class DotDict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def row_factory(cursor, row: tuple):
    keys = [col[0] for col in cursor.description]
    d = {k: v for k, v in zip(keys, row)}
    return DotDict(d)

async def _new_pool():
    return await aiosqlite.connect(
        CONSTS.db_path,
        autocommit=True,
    )

async def _get_pool(store=True, dict_row=False):
    if not store:
        return await _new_pool()

    if not hasattr(_get_pool, 'pools'):
        _get_pool.pools = {}
    
    stored_pool = 'pool_t' if dict_row else 'pool_dr'
    if pool := _get_pool.pools.get(stored_pool):
        return pool
    
    pool = await _new_pool()
    if dict_row:
        pool.row_factory = row_factory
    _get_pool.pools[stored_pool] = pool
    return pool




async def _run_query_fast(query: str, params: tuple=None):
    wait_pool = _get_pool()

    # patch query while waiting for the pool to connect on first connection
    query = patch_query(query)

    pool = await wait_pool
    async with pool.execute(query, params) as cursor:
        return await cursor.fetchall()


async def _run_query_dict(query: str, params=None, fetchone=False, commit=False):
    wait_pool = _get_pool(dict_row=True)
    query = patch_query(query) # patch query while waiting for the pool to connect on first connection
    pool = await wait_pool
    
    if sql_echo:
        print(query)
        print(params)
    
    async with pool.execute(query, params) as cursor:
        if commit:
            current_app.pool.commit()
            return
        if fetchone:
            return await cursor.fetchone()
        return await cursor.fetchall()


async def _close_pool():
    if not (pools := getattr(_get_pool, 'pools', None)):
        return
    await asyncio.gather(*(p.close() for p in pools.values()))
    delattr(_get_pool, 'pools')


re_mysql_bind_to_sqlite_bind = re.compile(r'%\((\w+)\)s')
def patch_query(query: str) -> str:
    """We write queries against MYSQL initially, then apply SQLITE patches with this function."""
    return re_mysql_bind_to_sqlite_bind.sub(r':\1', query).replace('`', '').replace('%s', '?').replace("strftime('?', ", "strftime('%s', ")


class SqlitePlaceholderGen(BasePlaceHolderGen):
    __slots__ = ()

    def __call__(self):
        return '?'

PlaceHolderGenerator = SqlitePlaceholderGen