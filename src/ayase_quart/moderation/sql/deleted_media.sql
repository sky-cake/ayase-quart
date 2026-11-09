CREATE TABLE IF NOT EXISTS deleted_media (
    deleted_media_id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_hash TEXT NOT NULL, -- b64 MD5 hash of the full media
    board_shortname TEXT NOT NULL,
    num INTEGER NOT NULL,
    thread_num INTEGER NOT NULL,
    user_id INTEGER NOT NULL, -- user_id of the mod/admin that deleted the post
    media_orig TEXT, -- full media filename e.g. 1696291733998594.jpg - needed to compute asagi fs paths
    preview_orig TEXT, -- thumbnail filename e.g. 1696291733998594s.jpg - needed to compute asagi fs paths
    deleted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (board_shortname, num, media_hash)
);
CREATE INDEX IF NOT EXISTS idx_deleted_media_media_hash ON deleted_media (media_hash);
