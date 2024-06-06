# Utilities

Before using any of these utilities, I suggest glancing at the code briefly to understand what is happening.

## Asagi Database Initializer

Initializes a database with tables, triggers, procedures, and indexes.

**How to run:** Configure `../src/configs.py`, and then run `python3 init_database.py`.

## Asagi Database Merger

Merges a new database into an older database. If this script is successful, it will leave the new database unaltered, even after running it numerous times. Here is essentially how it works,

- Asserts new and old databases each have no duplicate post nums.
- Deletes records in the old database that have the same post num as in the new database.
- Creates modified key columns like `modified_doc_id = doc_id + (select max(doc_id) from {db_old}.{board}) + 10;` on the new database tables `<board_name>`, and `<board_name>_images`.
- Does something similar with `media_id`s but also removes `media_hash` collisions since that's also a PK/unique.
- Inserts new database records into old database.
- Removes modified key columns.

**Note:** This script only merges the tables `<board_name>`, and `<board_name>_images`, the others are currently ignored. Also, mind the charsets and collations of the databases.

```sql
ALTER DATABASE `hayden`
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_general_ci;
```

**How to run:** Configure `consolidate_databases.py`, and then run `python3 consolidate_databases.py`.


## Extras

Wondering if your API scraper is working? Run this sql to list the latest posts.

```sql
-- 5 represents the hour offset from UTC
select 'ck' as board, timestamp, thread_num, num, comment, media_id
from ck where timestamp > UNIX_TIMESTAMP() - 50*60*5
order by timestamp desc
limit 12;
```