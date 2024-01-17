from templates import template_stats
from configs import CONSTS
from db import query_execute
from quart import Blueprint
from utils import render_controller

blueprint_admin = Blueprint('blueprint_admin', __name__, template_folder='templates')

# COLUMN_LIST = "doc_id, media_id, poster_ip, num, subnum, thread_num, op, timestamp, timestamp_expired, preview_orig, preview_w, preview_h, media_filename, media_w, media_h, media_size, media_hash, media_orig, spoiler, deleted, capcode, email, name, trip, title, comment, delpass, sticky, locked, poster_hash, poster_country, exif"
# INSERT_THREAD_INTO_DELETED = "INSERT INTO {board}_deleted SELECT * FROM {board} WHERE thread_num=:thread_num;"
# DELETE_THREAD = "DELETE FROM {board} WHERE thread_num=:thread_num;"
# INSERT_POST_INTO_DELETED = "INSERT INTO {board}_deleted SELECT * FROM {board} WHERE num=:num;"
# DELETE_POST = "DELETE FROM {board} WHERE num=:num;"

DATABASE_TABLE_STORAGE_SIZES = f"""select table_name as "Table Name", ROUND(SUM(data_length + index_length) / power(1024, 2), 1) as "Size in MB" from information_schema.tables where TABLE_SCHEMA = '{CONSTS.db_database}' group by table_name;"""
DATABASE_STORAGE_SIZE = f"""select table_schema "DB Name", ROUND(SUM(data_length + index_length) / power(1024, 2), 1) "Size in MB"  from information_schema.tables where table_schema = '{CONSTS.db_database}' group by table_schema;"""

@blueprint_admin.route("/stats")
async def stats():
    database_storage_size = await query_execute(DATABASE_STORAGE_SIZE)
    database_table_storage_sizes = await query_execute(DATABASE_TABLE_STORAGE_SIZES)
    return await render_controller(
        template_stats,
        database_storage_size=database_storage_size,
        database_table_storage_sizes=database_table_storage_sizes,
        **CONSTS.render_constants,
        title='Stats',
        tab_title="Stats",
    )
