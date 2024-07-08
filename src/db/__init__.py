from configs import CONSTS, DbType

from .db_interface import DatabaseInterface


def get_database_instance() -> DatabaseInterface:

    if CONSTS.db_type == DbType.mysql:
        from .db_mysql import MySQLDatabase
        return MySQLDatabase()

    elif CONSTS.db_type == DbType.sqlite:
        from .db_sqlite import SQLiteDatabase
        return SQLiteDatabase()

    else:
        raise ValueError("Unsupported database type")