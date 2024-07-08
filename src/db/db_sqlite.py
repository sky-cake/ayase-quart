import re

import aiosqlite
from quart import current_app

from configs import CONSTS

from .db_interface import DatabaseInterface, row_factory


class SQLiteDatabase(DatabaseInterface):    
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
        sql = sql.replace('%s', '?').replace("strftime('?', ", "strftime('%s', ") # I know...

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
