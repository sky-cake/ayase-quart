from templates import template_stats, template_latest, template_latest_gallery, template_latest_gallery_index
from configs import CONSTS
from db import query_execute
from quart import Blueprint
from utils import render_controller, validate_board_shortname
from asagi_converter import get_selector
from random import shuffle

blueprint_admin = Blueprint('blueprint_admin', __name__, template_folder='templates')

# COLUMN_LIST = "doc_id, media_id, poster_ip, num, subnum, thread_num, op, timestamp, timestamp_expired, preview_orig, preview_w, preview_h, media_filename, media_w, media_h, media_size, media_hash, media_orig, spoiler, deleted, capcode, email, name, trip, title, comment, delpass, sticky, locked, poster_hash, poster_country, exif"
# INSERT_THREAD_INTO_DELETED = "INSERT INTO {board}_deleted SELECT * FROM {board} WHERE thread_num=:thread_num;"
# DELETE_THREAD = "DELETE FROM {board} WHERE thread_num=:thread_num;"
# INSERT_POST_INTO_DELETED = "INSERT INTO {board}_deleted SELECT * FROM {board} WHERE num=:num;"
# DELETE_POST = "DELETE FROM {board} WHERE num=:num;"

DATABASE_TABLE_STORAGE_SIZES = """select table_name as "Table Name", ROUND(SUM(data_length + index_length) / power(1024, 2), 1) as "Size in MB" from information_schema.tables where TABLE_SCHEMA = %(db)s group by table_name;"""
DATABASE_STORAGE_SIZE = """select table_schema "DB Name", ROUND(SUM(data_length + index_length) / power(1024, 2), 1) "Size in MB"  from information_schema.tables where table_schema = %(db)s group by table_schema;"""


def get_sql_latest_ops(board_shortname):
    return f"""select '{board_shortname}' board_shortname, TIMESTAMPDIFF(MINUTE, FROM_UNIXTIME(timestamp + TIMESTAMPDIFF(SECOND, NOW(), UTC_TIMESTAMP())), NOW()) as elapsed_minutes, num, case when title is null then '' else title end as title, comment from {board_shortname} where op=1 order by num desc limit 5;"""


def get_sql_latest_gallery(board_shortname, limit=100):
    return f"""{get_selector(board_shortname)} from {board_shortname} where media_id is not null and media_filename is not null and media_filename not like '%.webm' order by timestamp desc limit {int(limit)};"""


@blueprint_admin.route("/stats")
async def stats():
    database_storage_size = await query_execute(DATABASE_STORAGE_SIZE, params={'db': CONSTS.db_database})
    database_table_storage_sizes = await query_execute(DATABASE_TABLE_STORAGE_SIZES, params={'db': CONSTS.db_database})
    return await render_controller(
        template_stats,
        database_storage_size=database_storage_size,
        database_table_storage_sizes=database_table_storage_sizes,
        **CONSTS.render_constants,
        title='Stats',
        tab_title="Stats",
    )


@blueprint_admin.route("/latest")
async def latest():
    threads = []
    for board_shortname in CONSTS.board_shortnames:
        sql = get_sql_latest_ops(board_shortname)
        latest_ops = await query_execute(sql)
        threads.extend(latest_ops)

    return await render_controller(
        template_latest,
        threads=threads,
        **CONSTS.render_constants,
        title='Latest',
        tab_title="Latest",
    )


@blueprint_admin.route("/latest_gallery")
async def latest_gallery():
    return await render_controller(
        template_latest_gallery_index,
        **CONSTS.render_constants,
        title='Gallery Index',
        tab_title="Gallery Index",
    )


@blueprint_admin.route("/latest_gallery/all")
async def latest_gallery_all():
    posts = []
    for board_shortname in CONSTS.board_shortnames:
        sql = get_sql_latest_gallery(board_shortname, limit=30)
        latest_media_posts = await query_execute(sql)
        if latest_media_posts:
            posts.extend(latest_media_posts)

    shuffle(posts)

    return await render_controller(
        template_latest_gallery,
        posts=posts,
        **CONSTS.render_constants,
        title='Latest gallery',
        tab_title='Latest gallery',
    )

@blueprint_admin.route("/latest_gallery/board/<string:board_shortname>")
async def latest_gallery_board(board_shortname):
    validate_board_shortname(board_shortname)

    sql = get_sql_latest_gallery(board_shortname)
    posts = await query_execute(sql)

    return await render_controller(
        template_latest_gallery,
        posts=posts,
        **CONSTS.render_constants,
        title=f'/{board_shortname}/ - gallery',
        tab_title=f'/{board_shortname}/ - gallery',
    )

