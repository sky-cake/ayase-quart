from dataclasses import dataclass

from enums import DbType
from configs import db_conf
from db import db_q

db_type: DbType = db_conf['db_type']

@dataclass
class SidetableTemplate:
    create_table: str = ''
    drop_table: str = ''
    add_index: str = ''
    drop_index: str = ''

    def get_command_template(self, command: str):
        match command:
            case 'create':
                return self.create_table
            case 'drop':
                return self.drop_table
            case 'dropindex':
                return self.drop_index
            case 'addindex':
                return self.add_index
            case _:
                return None

create_table_mysql = """
CREATE TABLE IF NOT EXISTS `%%BOARD%%_deleted` LIKE `%%BOARD%%`;

CREATE TABLE IF NOT EXISTS `%%BOARD%%_threads` (
    `thread_num` int unsigned NOT NULL,
    `time_op` int unsigned NOT NULL,
    `time_last` int unsigned NOT NULL,
    `time_bump` int unsigned NOT NULL,
    `time_ghost` int unsigned DEFAULT NULL,
    `time_ghost_bump` int unsigned DEFAULT NULL,
    `time_last_modified` int unsigned NOT NULL,
    `nreplies` int unsigned NOT NULL DEFAULT '0',
    `nimages` int unsigned NOT NULL DEFAULT '0',
    `sticky` bool NOT NULL DEFAULT '0',
    `locked` bool NOT NULL DEFAULT '0',

    PRIMARY KEY (`thread_num`)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `%%BOARD%%_images` (
    `media_id` int unsigned NOT NULL auto_increment,
    `media_hash` varchar(25) NOT NULL,
    `media` varchar(20),
    `preview_op` varchar(20),
    `preview_reply` varchar(20),
    `total` int(10) unsigned NOT NULL DEFAULT '0',
    `banned` smallint unsigned NOT NULL DEFAULT '0',

    PRIMARY KEY (`media_id`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_nopad_bin;

CREATE TABLE IF NOT EXISTS `%%BOARD%%_users` (
    `user_id` int unsigned NOT NULL auto_increment,
    `name` varchar(100) NOT NULL DEFAULT '',
    `trip` varchar(25) NOT NULL DEFAULT '',
    `firstseen` int(11) NOT NULL,
    `postcount` int(11) NOT NULL,

    PRIMARY KEY (`user_id`),
    UNIQUE name_trip_index (`name`, `trip`),
    INDEX firstseen_index (`firstseen`),
    INDEX postcount_index (`postcount`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `%%BOARD%%_daily` (
    `day` int(10) unsigned NOT NULL,
    `posts` int(10) unsigned NOT NULL,
    `images` int(10) unsigned NOT NULL,
    `sage` int(10) unsigned NOT NULL,
    `anons` int(10) unsigned NOT NULL,
    `trips` int(10) unsigned NOT NULL,
    `names` int(10) unsigned NOT NULL,

  PRIMARY KEY (`day`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

drop_table_mysql = """
DROP TABLE IF EXISTS `%%BOARD%%_daily`;
DROP TABLE IF EXISTS `%%BOARD%%_deleted`;
DROP TABLE IF EXISTS `%%BOARD%%_threads`;
DROP TABLE IF EXISTS `%%BOARD%%_images`;
DROP TABLE IF EXISTS `%%BOARD%%_users`;
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
"""

sidetable_templates = {
    DbType.mysql: SidetableTemplate(
        create_table=create_table_mysql,
        drop_table=drop_table_mysql,
        drop_index=drop_index_mysql,
        add_index=add_index_mysql,
    ),
}

def generate_from_template(template: str, boards: list[str]):
    return '\n'.join(
        template.replace('%%BOARD%%', board)
        for board in boards	
    )

async def run_table_command(command: str, boards: list[str]):
    if not (templates := sidetable_templates.get(db_type, None)):
        return
    if not (template := templates.get_command_template(command)):
        return
    try:
        sql = generate_from_template(template, boards)
        await db_q.query_tuple(sql)
    except Exception as e:
        raise e
    finally:
        await db_q.pool_manager.close_all_pools()
