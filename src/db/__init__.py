from typing import Callable
from functools import cache

from configs import CONSTS
from enums import DbType


@cache
def _get_db_module(db_type: DbType):
    match db_type:
        case DbType.mysql:
            from . import mysql
            return mysql
        case DbType.sqlite:
            from . import sqlite
            return sqlite
        case _:
            raise ValueError("Unsupported database type")


# pre connect so the first hit doesn't have connection latency
async def prime_db_pool():
    db_module = _get_db_module(CONSTS.db_type)
    await db_module._get_pool()


async def close_db_pool():
    db_module = _get_db_module(CONSTS.db_type)
    await db_module._close_pool()


def _get_tuple_query_fn() -> Callable:
    db_module = _get_db_module(CONSTS.db_type)
    return db_module._run_query_fast


def _get_dict_query_fn() -> Callable:
    db_module = _get_db_module(CONST.db_type)
    return db_module._run_query_dict


# only tuples for speed, no AttrDict/dotdicts
query_tuple: Callable = _get_tuple_query_fn()

query_dict: Callable = _get_dict_query_fn()

