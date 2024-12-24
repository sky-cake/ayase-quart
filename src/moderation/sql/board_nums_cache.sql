CREATE TABLE IF NOT EXISTS board_nums_cache (
    board_shortname TEXT NOT NULL,
    num INTEGER NOT NULL,
    op INTEGER NOT NULL,
    UNIQUE(board_shortname, num)
);
CREATE INDEX IF NOT EXISTS idx_board_shortname ON board_nums_cache (board_shortname);
CREATE INDEX IF NOT EXISTS idx_num ON board_nums_cache (num);
CREATE INDEX IF NOT EXISTS idx_op ON board_nums_cache (op);
CREATE INDEX IF NOT EXISTS idx_board_shortname_num ON board_nums_cache (board_shortname, num);
