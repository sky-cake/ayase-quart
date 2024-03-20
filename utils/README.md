# Utilities

Before using any of these utilities, I suggest glancing at the code briefly to understand what is happening.

1. To initialize a database, configure `../src/configs.py`, and then run `python3 init_database.py`.

2. To merge a new database into an older database, configure `consolidate_databases.py`, and then run `python3 consolidate_databases.py`.


## Extras

Wondering if your API scraper is working? Run this sql to list the latest posts.

```sql
-- 5 represents the hour offset from UTC
select 'ck' as board, timestamp, thread_num, num, comment, media_id from ck where timestamp > UNIX_TIMESTAMP() - 50*60*5
union
select 'g' as board, timestamp, thread_num, num, comment, media_id from g where timestamp > UNIX_TIMESTAMP() - 50*60*5
order by timestamp desc
limit 12;
```