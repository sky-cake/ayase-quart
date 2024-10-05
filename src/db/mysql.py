import aiomysql

from configs import CONSTS



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
            host=CONSTS.db_host,
            user=CONSTS.db_user,
            password=CONSTS.db_password,
            db=CONSTS.db_database,
            minsize=CONSTS.db_min_connections,
            maxsize=CONSTS.db_max_connections,
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


async def _close_pool():
    if not hasattr(_get_pool, 'pool'):
        return
    _get_pool.pool.close()
    await _get_pool.pool.wait_closed()
    delattr(_get_pool, 'pool')


