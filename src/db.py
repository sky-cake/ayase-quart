from quart import current_app
from loguru import logger
import aiomysql
from exceptions import QueryException


class AttrDict(dict):
    """Dict that can get attribute by dot, and doesn't raise KeyError"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return None


class AttrDictCursor(aiomysql.DictCursor):
    dict_type = AttrDict


async def query_handler(sql: str, fetchall: bool):
    try:
        async with current_app.db_pool.acquire() as connection:
            async with connection.cursor(AttrDictCursor) as cursor:
                await cursor.execute(sql)

                if fetchall:
                    return await cursor.fetchall()

                return await cursor.fetchone()
    except Exception as e:
        raise QueryException(e)


async def execute_handler(sql: str, values: list | dict, execute_many: bool):
    async with current_app.db_pool.acquire() as connection:
        async with connection.cursor() as cursor:
            result = {}
            try:
                if execute_many:
                    result = await cursor.execute_many(query=sql, values=values)
                else:
                    result = await cursor.execute(query=sql, values=values)
            except Exception as e:
                logger.error(f"Query failed!: {e}")
                await connection.rollback()
                return ""
            else:
                await connection.commit()
                return result
