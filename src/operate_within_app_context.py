from quart import Quart

from db import get_database_instance


async def operate_within_app_context(callback_to_execute):
    app = Quart(__name__)
    app.db = get_database_instance()

    async with app.app_context():
        try:
            await app.db.connect()
            await callback_to_execute()
        finally:
            await app.db.disconnect()
