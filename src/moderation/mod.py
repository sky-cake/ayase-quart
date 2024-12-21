from abc import ABC, abstractmethod

from aiosqlite import Connection

from asagi_converter import get_deleted_numops_by_board
from boards import board_shortnames
from configs import mod_conf
from db import db_m
from enums import DbPool, UserRole
from moderation.user import create_user
from utils import make_src_path, read_file


class BaseFilterCache(ABC):
    @classmethod
    async def init(cls):
        instance = cls()
        await instance.create_cache()
        cache_populated = await instance.is_cache_populated()
        if cache_populated:
            return
        await instance.populate_cache()

    @abstractmethod
    async def create_cache(self) -> None:
        """Create the db schema, filter in redis, whatever"""
        raise NotImplementedError()

    @abstractmethod
    async def is_cache_populated(self) -> bool:
        """Check if the population routine must be ran"""
        raise NotImplementedError()

    @abstractmethod
    async def populate_cache(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def teardown(self):
        """Remove all inserts"""
        raise NotImplementedError()

    async def print_cache_counts(self, stage: str) -> None:
        raise NotImplementedError()
    
    @staticmethod
    async def get_op_thread_removed_count(board_shortname: str) -> int:
        # if moderation is not activated, return 0
        raise NotImplementedError()
    
    @staticmethod
    async def get_board_num_pairs() -> set[tuple[str, int]]:
        raise NotImplementedError()
    
    @staticmethod
    async def is_post_removed(board_shortname: str, num: int) -> bool:
        raise NotImplementedError()


class FilterCacheBloom(BaseFilterCache):
    pass


class FilterCacheCuckoo(BaseFilterCache):
    pass


async def get_deleted_numops_per_board_iter():
    """Returns a tuple[str, tuple[int, int]]
    
    `(board_shortname, [(num, op), ...])`
    """
    if not mod_conf['hide_delete_posts']:
        return

    if not board_shortnames:
        return
    
    for board in board_shortnames:
        numops = await get_deleted_numops_by_board(board)
        print(board, numops)
        yield (board, numops)


class FilterCacheSqlite(BaseFilterCache):
    """Considered idempotent"""

    async def create_cache(self):
        """For now, just use the moderation sqlite database."""
        moderation_scripts = ['board_nums_cache.sql']
        for script in moderation_scripts:
            sqls = read_file(make_src_path('moderation', 'sql', script)).split(';')
            for sql in sqls:
                sql += ';' # important
                await db_m.query_dict(sql, p_id=DbPool.mod, commit=True)


    async def is_cache_populated(self):
        bn_count = (await db_m.query_tuple('select count(*) as bn_count from board_nums_cache', p_id=DbPool.mod))[0][0]
        return bool(bn_count)


    async def populate_cache(self):
        pool: Connection = await db_m.pool_manager.get_pool(p_id=DbPool.mod)

        await self.print_cache_counts('beginning 4chan staff inserts')

        # marked as deleted by 4chan staff
        ph = db_m.phg()
        async for board_and_numops in get_deleted_numops_per_board_iter():
            # board_and_numops -> (board_shortname, [(num, op), ...])
            if not board_and_numops[1]:
                continue

            sql = f"""insert or ignore into board_nums_cache (board_shortname, num, op) values ({ph}, {ph}, {ph})"""
            await pool.executemany(sql, [(board_and_numops[0], numop[0], numop[1]) for numop in board_and_numops[1]])
            await pool.commit()
            await self.print_cache_counts(board_and_numops[0])

        await self.print_cache_counts('beginning archive staff inserts')

        # marked as deleted by archive staff
        sql = 'select board_shortname, op, group_concat(distinct num) nums from reports group by board_shortname, op'
        rows = await db_m.query_tuple(sql, p_id=DbPool.mod)
        for board_op_nums in rows:
            sql = f"""insert or ignore into board_nums_cache (board_shortname, op, num) values ({ph}, {ph}, {ph})"""
            await pool.executemany(sql, [(board_op_nums[0], board_op_nums[1], num) for num in board_op_nums[2]])
            await pool.commit()
            await self.print_cache_counts(f'{board_op_nums[0]}, op = {board_op_nums[1]}')

        await self.print_cache_counts('done inserts')


    async def teardown(self):
        sql = """delete from board_nums_cache"""
        pool: Connection = await db_m.pool_manager.get_pool(p_id=DbPool.mod)
        await pool.execute(sql)
        await pool.commit()


    async def print_cache_counts(self, stage: str):
        count = (await db_m.query_tuple('select count(*) as bn_count from board_nums_cache', p_id=DbPool.mod))[0][0]
        print(f'Counts at {stage}: {count}')


    @staticmethod
    async def get_op_thread_removed_count(board_shortname: str) -> int:
        if not mod_conf['moderation']:
            return 0

        rows = await db_m.query_tuple(f'select count(*) from board_nums_cache where board_shortname = {db_m.phg()} and op = 1', params=[board_shortname])
        return rows[0][0]


    @staticmethod
    async def get_board_num_pairs(posts: list) -> set[tuple[str, int]]:
        board_and_nums = [(p['board_shortname'], p['num']) for p in posts]

        ph = ','.join([f'({db_m.phg()},{db_m.phg()})'] * len(board_and_nums))
        
        expanded = [item for bn in board_and_nums for item in bn]

        sql_string = f"""
            select board_shortname, num
            from board_nums_cache
            where (board_shortname, num) in ({ph})
        """
        rows = await db_m.query_tuple(sql_string, expanded)

        return {(row[0], row[1]) for row in rows}
    

    @staticmethod
    async def is_post_removed(board_shortname: str, num: int) -> bool:
        ph = db_m.phg()
        sql = f"""select num from board_nums_cache where board_shortname = {ph} and num = {ph}"""
        row = await db_m.query_tuple(sql, params=[board_shortname, num])
        if not row:
            return False
        return True


def _get_filter_cache() -> BaseFilterCache:
    match mod_conf['filter_cache_type']:
        case 'sqlite':
            return FilterCacheSqlite
        case _:
            raise NotImplementedError(mod_conf['filter_cache_type'])


async def init_moderation():
    moderation_scripts = ['users.sql', 'reports.sql']
    for script in moderation_scripts:
        await db_m.query_dict(read_file(make_src_path('moderation', 'sql', script)), p_id=DbPool.mod)

    user_count = (await db_m.query_dict('select count(*) user_count from users', p_id=DbPool.mod))[0].user_count
    if not user_count:
        admin_username = mod_conf['admin_user']
        admin_password = mod_conf['admin_password']

        await create_user(admin_username, admin_password, UserRole.admin, True, 'Remember to change your default password.')

    if not mod_conf['filter_cache']:
        return
    
    await f_cache.init()


async def filter_reported_posts(posts: list[dict], remove_op_replies=False) -> list:
    """If `remove_op_replies` is true, then replies to deleted OPs are removed.
    """

    if not mod_conf['moderation']:
        return posts

    if not posts:
        return posts

    board_num_pairs = await f_cache.get_board_num_pairs(posts)

    # len_i = len(posts)
    posts = [
        post
        for post in posts
        if not (remove_op_replies and (post['board_shortname'], post['thread_num']) in board_num_pairs)
        and not ((post['board_shortname'], post['num']) in board_num_pairs)
    ]
    # print(f'[MOD: removed post count /{posts[0]['board_shortname']}/: {len_i - len(posts)}]')
    return posts


async def is_post_removed(post: dict) -> bool:
    """Is the post removed?"""

    if not mod_conf['moderation']:
        return False

    if not post:
        raise ValueError(post)

    result = await f_cache.is_post_removed(post['board_shortname'], post['num'])
    return result


f_cache: BaseFilterCache = _get_filter_cache()
