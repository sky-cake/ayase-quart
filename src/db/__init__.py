import asyncio
from functools import wraps, cache

from configs import db_conf, db_mod_conf, db_archiveposting_conf
from db.base_db import BasePlaceHolderGen, BasePoolManager, BaseQueryRunner
from enums import DbPool, DbType

@cache
def _get_db_module(db_type: DbType):
    match db_type:
        case DbType.mysql:
            from .mysql import (
                MysqlPlaceholderGen,
                MysqlPoolManager,
                MysqlQueryRunner
            )
            return {
                'PoolManager': MysqlPoolManager,
                'QueryRunner': MysqlQueryRunner,
                'PlaceholderGenerator': MysqlPlaceholderGen,
            }
        case DbType.sqlite:
            from .sqlite import (
                SqlitePlaceholderGen,
                SqlitePoolManager,
                SqliteQueryRunner
            )
            return {
                'PoolManager': SqlitePoolManager,
                'QueryRunner': SqliteQueryRunner,
                'PlaceholderGenerator': SqlitePlaceholderGen,
            }
        case DbType.postgresql:
            from .postgresql import (
                PostgresqlPlaceholderGen,
                PostgresqlPoolManager,
                PostgresqlQueryRunner
            )
            return {
                'PoolManager': PostgresqlPoolManager,
                'QueryRunner': PostgresqlQueryRunner,
                'PlaceholderGenerator': PostgresqlPlaceholderGen,
            }
        case _:
            raise ValueError("Unsupported database type")


async def get_db_tables(db_conf: dict, db_type: DbType, close_pool_after=False) -> list[str]:
    '''Set `close_pool_after=True` if calling from a runtime that won't close the DB pool later.'''
    if not hasattr(get_db_tables, 'tables'):
        match db_type:
            case DbType.mysql:
                sql = 'SHOW TABLES;'
            case DbType.sqlite:
                sql = "SELECT name FROM sqlite_master WHERE type='table';"
            case DbType.postgres:
                sql = "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
            case _:
                return []

        db_h = DbHandler(db_conf, db_type)
        rows = await db_h.query_tuple(sql)
        get_db_tables.tables = [row[0] for row in rows]

        if close_pool_after:
            await db_h.close_db_pool()
    return get_db_tables.tables


class DbHandler:
    def __init__(self, db_conf: dict, db_type: DbType, pool_manager: BasePoolManager = None, query_runner: BaseQueryRunner = None):
        self.db_type = db_type
        self.db_module: dict = _get_db_module(db_type)
        self.pool_manager: BasePoolManager = pool_manager or self.db_module['PoolManager'](db_conf)
        self.query_runner: BaseQueryRunner = query_runner or self.db_module['QueryRunner'](self.pool_manager)
        self.phg: BasePlaceHolderGen = self.db_module['PlaceholderGenerator']() # "Place Holder Generator"
        self.length_method = 'CHAR_LENGTH' if db_type == DbType.mysql else 'LENGTH' # sqlite and pg

    async def prime_db_pool(self):
        await self.pool_manager.create_pool()

    async def close_db_pool(self):
        await self.pool_manager.close_pool()

    async def query_tuple(self, query: str, params=None, p_id=DbPool.main, commit=False):
        return await self.query_runner.run_query_fast(query, params=params, p_id=p_id, commit=commit)

    async def query_dict(self, query: str, params=None, commit=False, p_id=DbPool.main, dict_row=True):
        return await self.query_runner.run_query(query, params=params, commit=commit, p_id=p_id, dict_row=dict_row)
    
    async def run_script(self, query: str, p_id=DbPool.main):
        return await self.query_runner.run_script(query, p_id=p_id)


def close_all_databases(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)
        asyncio.run(db_q.pool_manager.close_all_pools())
        asyncio.run(db_m.pool_manager.close_all_pools())
    return wrapper


db_q = DbHandler(db_conf, db_conf['db_type']) # query
db_m = DbHandler(db_mod_conf, DbType.sqlite) # moderation, only supports sqlite atm
db_a = DbHandler(db_archiveposting_conf, DbType.sqlite) # archive
# db_t = DbHandler(db_tag_conf, DbType.sqlite)
# db_eav = DbHandler({'database': make_src_path('eav.db')}, DbType.sqlite)
