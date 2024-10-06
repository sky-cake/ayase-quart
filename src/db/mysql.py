import aiomysql

from configs import db_conf

from .base_db import BasePlaceHolderGen

sql_echo = db_conf.get('echo', False)
mysql_conf = db_conf.get('mysql', {})

class AttrDict(dict):
    """Dict that can get attribute by dot, and doesn't raise KeyError"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return None


class AttrDictCursor(aiomysql.DictCursor):
    dict_type = AttrDict


async def _get_pool(store=True):
    # we apply an attribute on this function to avoid polluting the module's namespace
    if not hasattr(_get_pool, 'pool') or not store:
        pool = await aiomysql.create_pool(
            **mysql_conf,
            autocommit=True,
        )
        if not store:
            return pool
        _get_pool.pool = pool
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


async def _run_query_dict(query: str, params=None, fetchone=False, commit=False):
        pool = await _get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(AttrDictCursor) as cursor:

                if sql_echo:
                    final_sql = cursor.mogrify(query, params)
                    print('::SQL::', final_sql, '')

                await cursor.execute(query, params)

                if commit:
                    return conn.commit()

                if fetchone:
                    return await cursor.fetchone()

                return await cursor.fetchall()


async def _close_pool():
    if not hasattr(_get_pool, 'pool'):
        return
    _get_pool.pool.close()
    await _get_pool.pool.wait_closed()
    delattr(_get_pool, 'pool')

class MysqlPlaceholderGen(BasePlaceHolderGen):
    __slots__ = ()

    def __call__(self):
        return '%s'

PlaceHolderGenerator = MysqlPlaceholderGen