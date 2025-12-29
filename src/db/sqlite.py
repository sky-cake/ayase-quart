import aiosqlite

from configs import mod_conf

from .base_db import BasePlaceHolderGen, BasePoolManager, BaseQueryRunner


class DotDict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def row_factory(cursor, row: tuple):
    keys = [col[0] for col in cursor.description]
    return DotDict({k: v for k, v in zip(keys, row)})


class SqlitePoolManager(BasePoolManager):
    def __init__(self, sqlite_conf=None, sql_echo=False):
        self.sqlite_conf = sqlite_conf or {}
        self.sql_echo = sql_echo
        self.pool = None


    async def get_pool(self, dict_row=False):
        if self.pool:
            self.pool.row_factory = row_factory if dict_row else None
            return self.pool

        db_path = self.sqlite_conf['database']
        load_sqlite_into_memory = self.sqlite_conf.get('load_sqlite_into_memory')

        if load_sqlite_into_memory:
            mem_pool = await aiosqlite.connect(':memory:')

            file_pool = await aiosqlite.connect(db_path)
            await file_pool.backup(mem_pool)
            await file_pool.close()

            pool = mem_pool

        else:
            pool = await aiosqlite.connect(db_path)

        pool.row_factory = row_factory if dict_row else None

        if mod_conf['enabled'] and mod_conf['regex_filter'] and mod_conf['path_to_regex_so']:
            await pool.enable_load_extension(True)
            await pool.load_extension(mod_conf['path_to_regex_so'])
            cur = await pool.execute('select regex_version();')
            await cur.fetchone()
            # regex_version = await cur.fetchone()
            # print(f'regex_version(): {regex_version}')

        self.pool = pool
        return self.pool


    async def close_pool(self):
        if self.pool is None:
            return

        await self.pool.close()


class SqliteQueryRunner(BaseQueryRunner):
    def __init__(self, pool_manager: SqlitePoolManager, sql_echo=False):
        self.pool_manager = pool_manager
        self.sql_echo = sql_echo


    async def run_query(self, query: str, params=None, commit=False, dict_row=True):
        pool = await self.pool_manager.get_pool(dict_row=dict_row)

        if self.sql_echo:
            print('::SQL::', query)
            print('::PARAMS::', params)

        async with pool.execute(query, params) as cursor:
            results = await cursor.fetchall()

            # commit comes after `fetchall` to support `returing` statements
            if commit:
                await pool.commit()

            return results


    async def run_query_fast(self, query: str, params=None, commit=False):
        return await self.run_query(query, params, dict_row=False, commit=commit)


    async def run_query_many(self, query: str, params=None, commit=False, dict_row=True):
        pool = await self.pool_manager.get_pool(dict_row=dict_row)

        if self.sql_echo:
            print('::SQL::', query)
            print('::PARAMS::', params)

        async with pool.executemany(query, params) as cursor:
            results = await cursor.fetchall()

            # commit comes after `fetchall` to support `returing` statements
            if commit:
                await pool.commit()

            return results
        

    async def run_script(self, query: str):
        pool = await self.pool_manager.get_pool()

        if self.sql_echo:
            print('::SQL::', query)

        await pool.executescript(query)
        await pool.commit()


class SqlitePlaceholderGen(BasePlaceHolderGen):
    __slots__ = ()

    def __call__(self):
        return '?'
