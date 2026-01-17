CREATE TABLE IF NOT EXISTS report_parent (
    report_parent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    board_shortname TEXT NOT NULL,
    op INTEGER NOT NULL,
    num INTEGER NOT NULL,
    thread_num INTEGER NOT NULL,
    public_access TEXT NOT NULL CHECK (public_access IN ('v', 'h')), -- visible (v), hidden (h)
    mod_status TEXT NOT NULL CHECK (mod_status IN ('o', 'c')), -- open (o), closed (c)
    mod_notes TEXT,
    last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (board_shortname, num)
);
