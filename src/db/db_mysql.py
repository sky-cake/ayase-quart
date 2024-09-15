import aiomysql
from quart import current_app

from configs import CONSTS

from .db_interface import DatabaseInterface


class AttrDict(dict):
    """Dict that can get attribute by dot, and doesn't raise KeyError"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return None


class AttrDictCursor(aiomysql.DictCursor):
    dict_type = AttrDict


class MySQLDatabaseAppContext(DatabaseInterface):
    async def connect(self):
        print('Creating database pool, started.')
        current_app.pool = await aiomysql.create_pool(
            host=CONSTS.db_host,
            user=CONSTS.db_user,
            password=CONSTS.db_password,
            db=CONSTS.db_database,
            minsize=CONSTS.db_min_connections,
            maxsize=CONSTS.db_max_connections,
            pool_recycle=30,  # renew pool connections every N seconds so data does not get stale
        )
        print('Creating database pool, completed.')

    async def query_execute(self, sql, params=None, fetchone=False, commit=False):
        async with current_app.pool.acquire() as conn:
            async with conn.cursor(AttrDictCursor) as cursor:

                if CONSTS.SQLALCHEMY_ECHO:
                    final_sql = cursor.mogrify(sql, params)
                    print('::SQL::', final_sql, '')

                await cursor.execute(sql, params)

                if commit:
                    return conn.commit()

                if fetchone:
                    return await cursor.fetchone()

                return await cursor.fetchall()

    async def disconnect(self):
        current_app.pool.close()
        await current_app.pool.wait_closed()


class MySQLDatabase(DatabaseInterface):
    def __init__(self):
        self.pool = None

    async def connect(self):
        print('Creating database pool, started.')
        self.pool = await aiomysql.create_pool(
            host=CONSTS.db_host,
            user=CONSTS.db_user,
            password=CONSTS.db_password,
            db=CONSTS.db_database,
            minsize=CONSTS.db_min_connections,
            maxsize=CONSTS.db_max_connections,
            pool_recycle=30,  # renew pool connections every N seconds so data does not get stale
        )
        print('Creating database pool, completed.')

    async def query_execute(self, sql, params=None, fetchone=False, commit=False):
        async with self.pool.acquire() as conn:
            async with conn.cursor(AttrDictCursor) as cursor:

                if CONSTS.SQLALCHEMY_ECHO:
                    final_sql = cursor.mogrify(sql, params)
                    print('::SQL::', final_sql, '')

                await cursor.execute(sql, params)

                if commit:
                    return conn.commit()

                if fetchone:
                    return await cursor.fetchone()

                return await cursor.fetchall()

    async def disconnect(self):
        if self.pool is not None:
            self.pool.close()
            await self.pool.wait_closed()

async def _get_pool():
    if not hasattr(_get_pool, 'pool'):
        _get_pool.pool = await aiomysql.create_pool(
            host=CONSTS.db_host,
            user=CONSTS.db_user,
            password=CONSTS.db_password,
            db=CONSTS.db_database,
            minsize=CONSTS.db_min_connections,
            maxsize=CONSTS.db_max_connections,
            autocommit=True,
        )
    return _get_pool.pool

async def _run_query_fast(query: str, params: tuple=None):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, params)
            res = [await cursor.fetchall()]
            while await cursor.nextset():
               res.append(await cursor.fetchall())
            if len(res) == 1:
                return res[0]
            return res

async def _close_pool():
    if not hasattr(_get_pool, 'pool'):
        return
    _get_pool.pool.close()
    await _get_pool.pool.wait_closed()
    delattr(_get_pool, 'pool')

Database = MySQLDatabase
DatabaseAppContext = MySQLDatabaseAppContext