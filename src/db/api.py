from configs import CONSTS, DbType
from db import get_database_instance
from meta import all_4chan_boards


async def get_boards_in_database():
    if CONSTS.db_type == DbType.mysql:
        sql_string = """select TABLE_NAME as name from information_schema.tables where TABLE_SCHEMA = %(name)s;"""
        assert CONSTS.db_database, CONSTS.db_database
        name = CONSTS.db_database

    elif CONSTS.db_type == DbType.sqlite:
        sql_string = """SELECT name FROM sqlite_master WHERE type=:name;"""
        name = 'table'

    db = get_database_instance(app_context=False)
    await db.connect()
    table_names = [row.name for row in await db.query_execute(sql_string, {'name': name})]
    await db.disconnect()

    if not table_names:
        raise ValueError('No tables found in the database.')

    boards_in_database = []
    for table_name in table_names:
        if table_name and table_name in all_4chan_boards and len(table_name) < 5:
            boards_in_database.append(table_name)
    return boards_in_database
