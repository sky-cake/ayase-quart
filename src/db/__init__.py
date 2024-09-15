from configs import CONSTS
from e_nums import DbType

from .db_interface import DatabaseInterface
from . import db_mysql as mysql, db_sqlite as sqlite

def get_database_instance(app_context=True) -> DatabaseInterface:
    db_module = _get_db_module(CONSTS.db_type)
    if app_context:
        if not hasattr(get_database_instance, 'db_app_context'):
            get_database_instance.db_app_context = db_module.DatabaseAppContext()
        return get_database_instance.db_app_context
    if not hasattr(get_database_instance, 'db'):
        get_database_instance.db = db_module.Database()
    return get_database_instance.db

def _get_db_module(db_type: DbType):
    match db_type:
        case DbType.mysql:
            return mysql
        case DbType.sqlite:
            return sqlite
        case _:
            raise ValueError("Unsupported database type")

# pre connect so so the first hit doesn't have connection latency
async def prime_db_pool():
    db_module = _get_db_module(CONSTS.db_type)
    await db_module._get_pool()

async def close_db_pool():
    db_module = _get_db_module(CONSTS.db_type)
    await db_module._close_pool()

def _get_tuple_query_fn():
    db_module = _get_db_module(CONSTS.db_type)
    return db_module._run_query_fast

# only tuples for speed, no AttrDict/dotdicts
query_tuple = _get_tuple_query_fn()