CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_no INTEGER,
    details TEXT NOT NULL,
    status TEXT NOT NULL,
    created_datetime TIMESTAMP NOT NULL,
    last_updated_datetime TIMESTAMP NOT NULL
);