-- some extra indexes to consider

CREATE INDEX %%BOARD%%_op_index_IDX ON `%%BOARD%%` (`op`);
CREATE INDEX %%BOARD%%_threads_time_bump_IDX USING BTREE ON `%%BOARD%%`_threads (time_bump);
