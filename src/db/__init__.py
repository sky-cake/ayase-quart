from configs import CONSTS, DbType

from .db_interface import DatabaseInterface


def get_database_instance(app_context=True) -> DatabaseInterface:
    if CONSTS.db_type == DbType.mysql:
        if app_context:
            from .db_mysql import MySQLDatabaseAppContext
            return MySQLDatabaseAppContext()

        from .db_mysql import MySQLDatabase
        return MySQLDatabase()

    elif CONSTS.db_type == DbType.sqlite:
        if app_context:
            from .db_sqlite import SQLiteDatabaseAppContext
            return SQLiteDatabaseAppContext()

        from .db_sqlite import SQLiteDatabase
        return SQLiteDatabase()

    else:
        raise ValueError("Unsupported database type")