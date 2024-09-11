set @exist := (select count(*)
    from information_schema.statistics
        where table_name = '%%BOARD%%' and index_name = '%%BOARD%%_comment_fts_index' and table_schema = database());

set @sql_statement := if(
    @exist > 0,
    'select ''INFO: Index %%BOARD%%_comment_fts_index already exists.''',
    'CREATE FULLTEXT INDEX `%%BOARD%%_comment_fts_index` ON `%%BOARD%%` (comment)'
);

PREPARE stmt FROM @sql_statement;

EXECUTE stmt; //
