CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    board_shortname TEXT NOT NULL,
    op INTEGER NOT NULL,
    num INTEGER NOT NULL,
    thread_num INTEGER NOT NULL,
    post_status TEXT NOT NULL, -- visible, hidden
    submitter_ip TEXT,
    submitter_notes TEXT,
    report_category TEXT NOT NULL, -- illegal, spam, dox, etc
    report_status TEXT NOT NULL, -- open, closed
    moderator_notes TEXT,
    created_at TIMESTAMP NOT NULL,
    last_updated_at TIMESTAMP NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
