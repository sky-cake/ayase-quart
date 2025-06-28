import aiomysql
from aiomysql.pool import _PoolContextManager

from enums import DbPool

from .base_db import BasePlaceHolderGen, BasePoolManager, BaseQueryRunner


class AttrDict(dict):
    """Dict that can get attributes via dot notation and avoids KeyError."""
    def __getattr__(self, name):
        return self.get(name, None)


class AttrDictCursor(aiomysql.DictCursor):
    dict_type = AttrDict


class MysqlPoolManager(BasePoolManager):
    def __init__(self, mysql_conf: dict | None=None):
        """
        `mysql_conf` is consumed by `aiomysql.create_pool` as kwargs. E.g. `host`, `port`, `db`, `user`, `minsize`, `maxsize`, etc.

        `autocommit` is set to `True` by default.
        """
        self.mysql_conf = mysql_conf or dict()
        self.pools = dict()

    async def create_pool(self, p_id=DbPool.main):
        if p_id in self.pools:
            return self.pools[p_id]

        d = dict(**self.mysql_conf['mysql'])
        d['autocommit'] = True

        pool = await aiomysql.create_pool(**d)
        self.pools[p_id] = pool
    
        return pool

    async def get_pool(self, p_id=DbPool.main, store=True):
        if not store:
            return await self.create_pool(self, p_id=p_id)
        return await self.create_pool(p_id)

    async def close_pool(self, p_id=DbPool.main):
        if p_id in self.pools:
            self.pools[p_id].close()
            await self.pools[p_id].wait_closed()
            del self.pools[p_id]

    async def close_all_pools(self):
        for p_id in list(self.pools.keys()):
            await self.close_pool(p_id)


class MysqlQueryRunner(BaseQueryRunner):
    def __init__(self, pool_manager: MysqlPoolManager, sql_echo=False):
        self.pool_manager = pool_manager
        self.sql_echo = sql_echo

    async def run_query(self, query: str, params=None, commit=False, p_id=DbPool.main, dict_row=True):
        pool: _PoolContextManager = await self.pool_manager.get_pool(p_id)
        cursor_class = AttrDictCursor if dict_row else aiomysql.Cursor

        async with pool.acquire() as conn:
            async with conn.cursor(cursor_class) as cursor:
                if self.sql_echo:
                    final_sql = cursor.mogrify(query, params)
                    print('::SQL::', final_sql, '')

                await cursor.execute(query, params)

                results = [await cursor.fetchall()]
                while await cursor.nextset():
                    results.append(await cursor.fetchall())

                if commit:
                    await conn.commit()

                return results[0] if len(results) == 1 else results # prone to issues ?

    async def run_query_fast(self, query: str, params=None, p_id=DbPool.main, commit=False):
        return await self.run_query(query, params, p_id=p_id, dict_row=False, commit=commit)


    async def run_query_many(self, query: str, params=None, commit=False, p_id=DbPool.main, dict_row=True):
        pool: _PoolContextManager = await self.pool_manager.get_pool(p_id)
        cursor_class = AttrDictCursor if dict_row else aiomysql.Cursor

        async with pool.acquire() as conn:
            async with conn.cursor(cursor_class) as cursor:
                if self.sql_echo:
                    final_sql = cursor.mogrify(query, params)
                    print('::SQL::', final_sql, '')

                await cursor.executemany(query, params)

                results = [await cursor.fetchall()]
                while await cursor.nextset():
                    results.append(await cursor.fetchall())

                if commit:
                    await conn.commit()

                return results[0] if len(results) == 1 else results # prone to issues ?
    
    async def run_script(self, query: str, p_id=DbPool.main):
        return await self.run_query_fast(query, p_id=p_id, commit=True)


class MysqlPlaceholderGen(BasePlaceHolderGen):
    __slots__ = ()

    def __call__(self):
        return '%s'
