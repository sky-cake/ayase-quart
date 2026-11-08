from typing import Optional

from ..db import db_m


async def record_deleted_media(post: dict, user_id: int) -> bool:
    media_hash = post.get('media_hash')
    if not media_hash:
        return False

    params = [
        media_hash,
        post['board_shortname'],
        post['num'],
        post['thread_num'],
        user_id,
    ]
    sql = f"""
        insert or ignore into
            deleted_media (media_hash, board_shortname, num, thread_num, user_id)
        values ({db_m.Phg().size(params)})
        returning deleted_media_id
    ;"""
    rows = await db_m.query_dict(sql, params=params, commit=True)
    return bool(rows)


async def get_deleted_media(
    media_hash: Optional[str] = None,
    board_shortname: Optional[str] = None,
    num: Optional[int] = None,
    limit: int = 100,
) -> list[dict]:
    phg = db_m.Phg()
    where = []
    params = []

    if media_hash:
        where.append(f'media_hash = {phg()}')
        params.append(media_hash)
    if board_shortname:
        where.append(f'board_shortname = {phg()}')
        params.append(board_shortname)
    if num:
        where.append(f'num = {phg()}')
        params.append(num)

    sql = 'select * from deleted_media'
    if where:
        sql += ' where ' + ' and '.join(where)
    sql += f' order by deleted_at desc limit {phg()};'
    params.append(limit)

    rows = await db_m.query_dict(sql, params=params)
    return rows if rows else []


async def is_media_hash_deleted(media_hash: str) -> bool:
    sql = f'select 1 from deleted_media where media_hash = {db_m.Phg()()} limit 1;'
    rows = await db_m.query_dict(sql, params=(media_hash,))
    return bool(rows)


async def get_deleted_media_count() -> int:
    rows = await db_m.query_dict('select count(*) as deleted_media_count from deleted_media;')
    if rows:
        return rows[0]['deleted_media_count']
    return 0
