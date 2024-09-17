import re

import aiosqlite
from quart import current_app

from configs import CONSTS

from .db_interface import DatabaseInterface, row_factory


class SQLiteDatabaseAppContext(DatabaseInterface):
    async def connect(self):
        print('Creating database pool, started.')
        current_app.pool = await aiosqlite.connect(CONSTS.db_path)
        current_app.pool.row_factory = row_factory
        print('Creating database pool, completed.')

    async def disconnect(self):
        await current_app.pool.close()

    async def query_execute(self, sql, params=None, fetchone=False, commit=False):
        pattern = r'%\((\w+)\)s'
        # replace %(name)s with :name
        sql = re.sub(pattern, r':\1', sql)

        sql = sql.replace('`', '')
        sql = sql.replace('%s', '?').replace("strftime('?', ", "strftime('%s', ")  # I know...

        if CONSTS.SQLALCHEMY_ECHO:
            print(sql)
            print(params)

        async with current_app.pool.execute(sql, params) as cursor:

            if commit:
                current_app.pool.commit()
                return

            if fetchone:
                return await cursor.fetchone()

            return await cursor.fetchall()


class SQLiteDatabase(DatabaseInterface):
    def __init__(self):
        self.pool = None

    async def connect(self):
        print('Creating database pool, started.')
        self.pool = await aiosqlite.connect(CONSTS.db_path)
        self.pool.row_factory = row_factory
        print('Creating database pool, completed.')

    async def disconnect(self):
        await self.pool.close()

    async def query_execute(self, sql, params=None, fetchone=False, commit=False):
        pattern = r'%\((\w+)\)s'
        # replace %(name)s with :name
        sql = re.sub(pattern, r':\1', sql)

        sql = sql.replace('`', '')
        sql = sql.replace('%s', '?').replace("strftime('?', ", "strftime('%s', ")  # I know...

        if CONSTS.SQLALCHEMY_ECHO:
            print(sql)
            print(params)

        async with self.pool.execute(sql, params) as cursor:

            if commit:
                self.pool.commit()
                return

            if fetchone:
                return await cursor.fetchone()

            return await cursor.fetchall()


async def _get_pool():
    if not hasattr(_get_pool, 'pool'):
        _get_pool.pool = await aiosqlite.connect(
            CONSTS.db_path,
            autocommit=True,
        )
    return _get_pool.pool

async def _run_query_fast(query: str, params: tuple=None):
    wait_pool = _get_pool()

    # patch query while waiting for the pool to connect on first connection
    query = patch_query(query)

    pool = await wait_pool
    async with pool.execute(query, params) as cursor:
        res = [await cursor.fetchall()]
        while await cursor.nextset():
            res.append(await cursor.fetchall())
        if len(res) == 1:
            return res[0]
        return res

async def _close_pool():
    if not hasattr(_get_pool, 'pool'):
        return
    await _get_pool.pool.close()
    delattr(_get_pool, 'pool')

re_colon = re.compile(r'%\((\w+)\)s')
def patch_query(query: str):
    return re_colon.sub(r':\1', query).replace('`', '').replace('%s', '?').replace("strftime('?', ", "strftime('%s', ")


Database = SQLiteDatabase
DatabaseAppContext = SQLiteDatabaseAppContext