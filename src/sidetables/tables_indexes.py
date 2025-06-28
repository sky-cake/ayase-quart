from dataclasses import dataclass

from enums import DbType
from configs import db_conf
from db import db_q
from . import SideTableCmd as Cmd

db_type: DbType = db_conf['db_type']
backup_suffix = 'bak'

@dataclass
class SidetableTemplate:
    create_table: str = ''
    drop_table: str = ''
    backup_table: str = ''
    add_index: str = ''
    drop_index: str = ''

    def get_command_template(self, command: str):
        match command:
            case Cmd.table_create:
                return self.create_table
            case Cmd.table_drop:
                return self.drop_table
            case Cmd.table_backup:
                return self.backup_table
            case Cmd.index_drop:
                return self.drop_index
            case Cmd.index_add:
                return self.add_index
            case _:
                return None

create_table_mysql = """
create table if not exists `%%BOARD%%_deleted` like `%%BOARD%%`;

create table if not exists `%%BOARD%%_threads` (
    `thread_num` int unsigned not null,
    `time_op` int unsigned not null,
    `time_last` int unsigned not null,
    `time_bump` int unsigned not null,
    `time_ghost` int unsigned default null,
    `time_ghost_bump` int unsigned default null,
    `time_last_modified` int unsigned not null,
    `nreplies` int unsigned not null default '0',
    `nimages` int unsigned not null default '0',
    `sticky` bool not null default '0',
    `locked` bool not null default '0',

    primary key (`thread_num`)
) ENGINE=InnoDB CHARSET=utf8mb4;

create table if not exists `%%BOARD%%_images` (
    `media_id` int unsigned not null auto_increment,
    `media_hash` varchar(25) not null,
    `media` varchar(20),
    `preview_op` varchar(20),
    `preview_reply` varchar(20),
    `total` int(10) unsigned not null default '0',
    `banned` smallint unsigned not null default '0',

    primary key (`media_id`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin;

create table if not exists `%%BOARD%%_users` (
    `user_id` int unsigned not null auto_increment,
    `name` varchar(100) not null default '',
    `trip` varchar(25) not null default '',
    `firstseen` int(11) not null,
    `postcount` int(11) not null,

    primary key (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

create table if not exists `%%BOARD%%_daily` (
    `day` int(10) unsigned not null,
    `posts` int(10) unsigned not null,
    `images` int(10) unsigned not null,
    `sage` int(10) unsigned not null,
    `anons` int(10) unsigned not null,
    `trips` int(10) unsigned not null,
    `names` int(10) unsigned not null,

    primary key (`day`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

drop_table_mysql = """
drop table if exists `%%BOARD%%_daily`;
drop table if exists `%%BOARD%%_deleted`;
drop table if exists `%%BOARD%%_threads`;
drop table if exists `%%BOARD%%_images`;
drop table if exists `%%BOARD%%_users`;
"""

backup_table_mysql = f"""
rename table `%%BOARD%%_daily` to `%%BOARD%%_daily_{backup_suffix}`;
rename table `%%BOARD%%_deleted` to `%%BOARD%%_deleted_{backup_suffix}`;
rename table `%%BOARD%%_images` to `%%BOARD%%_images_{backup_suffix}`;
rename table `%%BOARD%%_threads` to `%%BOARD%%_threads_{backup_suffix}`;
rename table `%%BOARD%%_users` to `%%BOARD%%_users_{backup_suffix}`;
"""

drop_index_mysql = """
drop index `time_op_index` on `%%BOARD%%_threads`;
drop index `time_bump_index` on `%%BOARD%%_threads`;
drop index `time_ghost_bump_index` on `%%BOARD%%_threads`;
drop index `time_last_modified_index` on `%%BOARD%%_threads`;
drop index `sticky_index` on `%%BOARD%%_threads`;
drop index `locked_index` on `%%BOARD%%_threads`;

drop index `media_hash_index` on `%%BOARD%%_images`;
drop index `total_index` on `%%BOARD%%_images`;
drop index `banned_index` on `%%BOARD%%_images`;

drop index `name_trip_index` on `%%BOARD%%_users`;
drop index `firstseen_index` on `%%BOARD%%_users`;
drop index `postcount_index` on `%%BOARD%%_users`;
"""

add_index_mysql = """
alter table `%%BOARD%%_threads` add index `time_op_index` (`time_op`);
alter table `%%BOARD%%_threads` add index `time_bump_index` (`time_bump`);
alter table `%%BOARD%%_threads` add index `time_ghost_bump_index` (`time_ghost_bump`);
alter table `%%BOARD%%_threads` add index `time_last_modified_index` (`time_last_modified`);
alter table `%%BOARD%%_threads` add index `sticky_index` (`sticky`);
alter table `%%BOARD%%_threads` add index `locked_index` (`locked`);

alter table `%%BOARD%%_images` add unique index `media_hash_index` (`media_hash`);
alter table `%%BOARD%%_images` add index `total_index` (`total`);
alter table `%%BOARD%%_images` add index `banned_index` (`banned`);

alter table `%%BOARD%%_users` add unique index name_trip_index (`name`, `trip`);
alter table `%%BOARD%%_users` add index firstseen_index (`firstseen`);
alter table `%%BOARD%%_users` add index postcount_index (`postcount`);
"""

create_table_sqlite = """
create table if not exists `%%BOARD%%_deleted` (
    doc_id integer not null primary key autoincrement,
    media_id integer not null,
    poster_ip text not null,
    num integer not null,
    subnum integer not null,
    thread_num integer not null,
    op integer not null,
    timestamp integer not null,
    timestamp_expired integer not null,
    preview_orig text,
    preview_w integer not null,
    preview_h integer not null,
    media_filename text,
    media_w integer not null,
    media_h integer not null,
    media_size integer not null,
    media_hash text,
    media_orig text,
    spoiler integer not null,
    deleted integer not null,
    capcode text not null,
    email text,
    name text,
    trip text,
    title text,
    comment text,
    delpass text,
    sticky integer not null,
    locked integer not null,
    poster_hash text,
    poster_country text,
    exif text
);

create table if not exists `%%BOARD%%_threads` (
    thread_num integer not null primary key,
    time_op integer not null,
    time_last integer not null,
    time_bump integer not null,
    time_ghost integer,
    time_ghost_bump integer,
    time_last_modified integer not null,
    nreplies integer not null,
    nimages integer not null,
    sticky integer not null,
    locked integer not null
);

create table if not exists `%%BOARD%%_images` (
    media_id integer not null primary key autoincrement,
    media_hash text not null,
    media text,
    preview_op text,
    preview_reply text,
    total integer not null,
    banned integer not null
);

create table if not exists `%%BOARD%%_users` (
    user_id integer not null primary key autoincrement,
    name text not null,
    trip text not null,
    firstseen integer not null,
    postcount integer not null
);

create table if not exists `%%BOARD%%_daily` (
    day integer not null primary key,
    posts integer not null,
    images integer not null,
    sage integer not null,
    anons integer not null,
    trips integer not null,
    names integer not null
);
"""

drop_table_sqlite = """
drop table if exists `%%BOARD%%_daily`;
drop table if exists `%%BOARD%%_deleted`;
drop table if exists `%%BOARD%%_threads`;
drop table if exists `%%BOARD%%_images`;
drop table if exists `%%BOARD%%_users`;
"""

backup_table_sqlite = f"""
alter table `%%BOARD%%_daily` rename to `%%BOARD%%_daily_{backup_suffix}`;
alter table `%%BOARD%%_deleted` rename to `%%BOARD%%_deleted_{backup_suffix}`;
alter table `%%BOARD%%_images` rename to `%%BOARD%%_images_{backup_suffix}`;
alter table `%%BOARD%%_threads` rename to `%%BOARD%%_threads_{backup_suffix}`;
alter table `%%BOARD%%_users` rename to `%%BOARD%%_users_{backup_suffix}`;
"""

drop_index_sqlite = """
drop index if exists `%%BOARD%%_threads_time_op_index`;
drop index if exists `%%BOARD%%_threads_time_bump_index`;
drop index if exists `%%BOARD%%_threads_time_ghost_bump_index`;
drop index if exists `%%BOARD%%_threads_time_last_modified_index`;
drop index if exists `%%BOARD%%_threads_sticky_index`;
drop index if exists `%%BOARD%%_threads_locked_index`;

drop index if exists `%%BOARD%%_images_media_hash_index`;
drop index if exists `%%BOARD%%_images_total_index`;
drop index if exists `%%BOARD%%_images_banned_index`;

drop index if exists `%%BOARD%%_users_name_trip_index`;
drop index if exists `%%BOARD%%_users_firstseen_index`;
drop index if exists `%%BOARD%%_users_postcount_index`;
"""

add_index_sqlite = """
create index if not exists `%%BOARD%%_threads_time_op_index` on `%%BOARD%%_threads` (`time_op`);
create index if not exists `%%BOARD%%_threads_time_bump_index` on `%%BOARD%%_threads` (`time_bump`);
create index if not exists `%%BOARD%%_threads_time_ghost_bump_index` on `%%BOARD%%_threads` (`time_ghost_bump`);
create index if not exists `%%BOARD%%_threads_time_last_modified_index` on `%%BOARD%%_threads` (`time_last_modified`);
create index if not exists `%%BOARD%%_threads_sticky_index` on `%%BOARD%%_threads` (`sticky`);
create index if not exists `%%BOARD%%_threads_locked_index` on `%%BOARD%%_threads` (`locked`);

create unique index if not exists %%BOARD%%_images_media_hash_index on `%%BOARD%%_images` (media_id);
create index if not exists %%BOARD%%_images_total_index on `%%BOARD%%_images` (`total`);
create index if not exists %%BOARD%%_images_banned_index on `%%BOARD%%_images` (`banned`);

create unique index if not exists %%BOARD%%_users_name_trip_index on `%%BOARD%%_users` (`name`, `trip`);
create index if not exists %%BOARD%%_users_firstseen_index on `%%BOARD%%_users` (`firstseen`);
create index if not exists %%BOARD%%_users_postcount_index on `%%BOARD%%_users` (`postcount`);
"""

sidetable_templates = {
    DbType.mysql: SidetableTemplate(
        create_table=create_table_mysql,
        drop_table=drop_table_mysql,
        backup_table=backup_table_mysql,
        drop_index=drop_index_mysql,
        add_index=add_index_mysql,
    ),
    DbType.sqlite: SidetableTemplate(
        create_table=create_table_sqlite,
        drop_table=drop_table_sqlite,
        backup_table=backup_table_sqlite,
        drop_index=drop_index_sqlite,
        add_index=add_index_sqlite,
    ),
}


def generate_from_template(template: str, boards: list[str]):
    return '\n'.join(
        template.replace('%%BOARD%%', board)
        for board in boards	
    )


async def run_table_command(command: str, boards: list[str]):
    if not (templates := sidetable_templates.get(db_type, None)):
        print(f'Table command not supported for database {db_type}')
        return
    if not (template := templates.get_command_template(command)):
        print(f'Table command {command} not found.')
        return
    try:
        sql = generate_from_template(template, boards)
        await db_q.run_script(sql)
    except Exception as e:
        raise e
    finally:
        await db_q.pool_manager.close_all_pools()
