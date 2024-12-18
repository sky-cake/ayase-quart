CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT,
    active BOOLEAN NOT NULL DEFAULT 1,
    role TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    last_update_at TIMESTAMP NOT NULL,
    last_login_at TIMESTAMP,
    notes TEXT
);