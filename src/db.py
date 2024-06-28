from quart import current_app

from configs import CONSTS

if CONSTS.db_aiomysql:
    import aiomysql

    class AttrDict(dict):
        """Dict that can get attribute by dot, and doesn't raise KeyError"""

        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError:
                return None


    class AttrDictCursor(aiomysql.DictCursor):
        dict_type = AttrDict

    async def query_execute(sql, params=None, fetchone=False, commit=False):
        async with current_app.db_pool.acquire() as connection:
            async with connection.cursor(AttrDictCursor) as cursor:

                if CONSTS.SQLALCHEMY_ECHO:
                    final_sql = cursor.mogrify(sql, params)
                    print('::SQL::', final_sql, '')

                await cursor.execute(sql, params)

                if commit:
                    return connection.commit()

                if fetchone:
                    return await cursor.fetchone()
                
                return await cursor.fetchall()
            

    async def db_pool_open():
        print('Creating database pool, started.')
        current_app.db_pool = await aiomysql.create_pool(
            host=CONSTS.db_host,
            user=CONSTS.db_user,
            password=CONSTS.db_password,
            db=CONSTS.db_database,
            minsize=CONSTS.db_min_connections,
            maxsize=CONSTS.db_max_connections,
            pool_recycle=30 # renew pool connections every N seconds so data does not get stale
        )
        print('Creating database pool, completed.')


    async def db_pool_close():
        current_app.db_pool.close()
        await current_app.db_pool.wait_closed()

elif CONSTS.db_aiosqlite:
    import re

    import aiosqlite


    class dotdict(dict):
        """dot.notation access to dictionary attributes"""
        __getattr__ = dict.get
        __setattr__ = dict.__setitem__
        __delattr__ = dict.__delitem__


    def row_factory(cursor, data):
        keys = [col[0] for col in cursor.description]
        d = {k: v for k, v in zip(keys, data)}
        return dotdict(d)


    async def query_execute(sql, params=None, fetchone=False, commit=False):
        pattern = r'%\((\w+)\)s'
        # replace %(name)s with :name
        sql = re.sub(pattern, r':\1', sql)

        sql = sql.replace('`', '')
        sql = sql.replace('%s', '?').replace("strftime('?', ", "strftime('%s', ") # I know...

        if CONSTS.SQLALCHEMY_ECHO:
            print(sql)
            print(params)

        async with current_app.db_pool.execute(sql, params) as cursor:

            if commit:
                current_app.db_pool.commit()
                return

            if fetchone:
                return await cursor.fetchone()
            
            return await cursor.fetchall()
            

    async def db_pool_open():
        print('Creating database pool, started.')
        current_app.db_pool = await aiosqlite.connect(CONSTS.db_path)
        current_app.db_pool.row_factory = row_factory
        print('Creating database pool, completed.')


    async def db_pool_close():
        await current_app.db_pool.close()

else:
    raise ValueError(CONSTS.db_aiomysql, CONSTS.db_aiosqlite)
