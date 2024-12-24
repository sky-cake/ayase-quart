CREATE TABLE IF NOT EXISTS report_child (
    report_child_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_parent_id INTEGER NOT NULL,
    submitter_ip TEXT,
    submitter_category TEXT NOT NULL, -- illegal, spam, dox, etc
    submitter_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (report_parent_id, submitter_ip),
    FOREIGN KEY (report_parent_id) REFERENCES report_parent (report_parent_id) ON DELETE CASCADE ON UPDATE CASCADE
);
