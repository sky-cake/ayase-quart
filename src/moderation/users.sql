CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT,
    active BOOLEAN NOT NULL DEFAULT 1,
    role TEXT NOT NULL,
    created_datetime TIMESTAMP NOT NULL,
    last_login_datetime TIMESTAMP NOT NULL,
    notes TEXT
);