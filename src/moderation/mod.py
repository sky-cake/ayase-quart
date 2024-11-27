from quart import flash
from enums import DbPool
from db import db_m
from enums import UserRole
from configs import moderation_conf
from moderation.user import create_user
from utils import make_src_path, read_file

async def init_moderation_db():
    moderation_scripts = ['users.sql', 'reports.sql']
    for script in moderation_scripts:
        await db_m.query_dict(read_file(make_src_path('moderation', script)), p_id=DbPool.mod)

    user_count = (await db_m.query_dict('select count(*) user_count from users;', p_id=DbPool.mod))[0].user_count
    if not user_count:
        admin_username = moderation_conf.get('admin_user')
        admin_password = moderation_conf.get('admin_password')
        await create_user(admin_username, admin_password, UserRole.admin, True, 'Remember to change your default password.')
        # await flash('Initial admin user created.')
