from configs import mod_conf
from db import db_m
from enums import DbPool
from moderation.user import Permissions, create_user_if_not_exists
from utils import make_src_path, read_file
from moderation.filter_cache import get_filter_cache, BaseFilterCache


async def init_moderation():
    moderation_scripts = ['users.sql', 'user_permissions.sql', 'report_parent.sql', 'report_child.sql', 'message.sql']
    for script in moderation_scripts:
        await db_m.query_dict(read_file(make_src_path('moderation', 'sql', script)), p_id=DbPool.mod)

    user_count = (await db_m.query_dict('select count(*) user_count from users', p_id=DbPool.mod))[0].user_count
    if not user_count:
        admin_username = mod_conf['admin_user']
        admin_password = mod_conf['admin_password']

        await create_user_if_not_exists(admin_username, admin_password, True, True, set([p for p in Permissions]), notes=None)


fc: BaseFilterCache = get_filter_cache(mod_conf)
