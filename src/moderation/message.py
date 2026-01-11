from datetime import datetime, timezone

from ..db import db_m


async def create_message(username: str, title: str, comment: str) -> None:
    sql = f'''
        insert into messages (username, title, comment, created_at)
        values ({db_m.Phg().qty(4)})
    '''
    timestamp_utc = datetime.now(timezone.utc)
    await db_m.query_dict(sql, params=(username, title, comment, timestamp_utc), commit=True)


async def get_messages_from_last_30_days() -> list[dict]:
    sql = '''select created_at, username, title, comment from messages where created_at >= datetime('now', '-30 days') order by created_at desc limit 100;'''
    rows = await db_m.query_dict(sql)
    if not rows:
        return []
    return rows
