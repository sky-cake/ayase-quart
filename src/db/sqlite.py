import asyncio
import re

import aiosqlite

from configs import db_conf

from .base_db import BasePlaceHolderGen

sql_echo = db_conf.get('echo', False)
sqlite_conf = db_conf.get('sqlite', {})

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
        **sqlite_conf,
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
    pool = await _get_pool()

    async with pool.execute(query, params) as cursor:
        return await cursor.fetchall()


async def _run_query_dict(query: str, params=None, commit=False):
    pool = await _get_pool(dict_row=True)
    
    if sql_echo:
        print(query)
        print(params)
    
    async with pool.execute(query, params) as cursor:
        if commit:
            pool.commit()
            return
        return await cursor.fetchall()


async def _close_pool():
    if not (pools := getattr(_get_pool, 'pools', None)):
        return
    await asyncio.gather(*(p.close() for p in pools.values()))
    del _get_pool.pools


class SqlitePlaceholderGen(BasePlaceHolderGen):
    __slots__ = ()

    def __call__(self):
        return '?'

PlaceHolderGenerator = SqlitePlaceholderGen