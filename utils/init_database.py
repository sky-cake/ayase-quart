import sys
import os
import asyncio
import aiomysql

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from configs import CONSTS


BOARD_PLACEHOLDER = '%%BOARD%%'
DATABASE_PLACEHOLDER = '%%DATABASE%%'
DELIMITER = '//'


def make_path(*path):
    return os.path.join(os.path.dirname(__file__), *path)


async def execute_sql(connection, cursor, board, filename):    
    with open(make_path(filename), encoding='utf-8') as f:
        print(filename)
        sql_string = f.read().replace(BOARD_PLACEHOLDER, board).replace(DATABASE_PLACEHOLDER, CONSTS.db_database)
        sql_strings = [x.strip() for x in sql_string.split(DELIMITER) if x.strip()]
        for sql_string in sql_strings:
            await cursor.execute(sql_string)
            await connection.commit()


async def main(loop):
    pool = await aiomysql.create_pool(host=CONSTS.db_host, user=CONSTS.db_user, password=CONSTS.db_password, minsize=1, maxsize=1, loop=loop)
    async with pool.acquire() as connection:
        async with connection.cursor() as cursor:
            await execute_sql(connection, cursor, '', 'create_database.sql')

    pool = await aiomysql.create_pool(host=CONSTS.db_host, user=CONSTS.db_user, password=CONSTS.db_password, db=CONSTS.db_database, minsize=1, maxsize=1, loop=loop)
    async with pool.acquire() as connection:
        async with connection.cursor() as cursor:
            for board in CONSTS.board_shortnames:
                print(f'Creating database objects for: {board}')
                await execute_sql(connection, cursor, board, 'create_asagi_schema.sql')
                await execute_sql(connection, cursor, board, 'create_asagi_triggers.sql')

                # if CONSTS.search: # might use lnx or elasticsearch for FTS since I'm not sure how MySQL scales with its native FTS
                #     await execute_sql(connection, cursor, board, 'create_asagi_search_indexes.sql')
                print()

    pool.close()
    await pool.wait_closed()


if __name__=='__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    print('Done.')
