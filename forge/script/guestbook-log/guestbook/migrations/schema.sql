CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_utc TEXT NOT NULL,
    updated_utc TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'spam', 'hidden')),
    display_name TEXT NOT NULL,
    comment_raw TEXT NOT NULL,
    comment_rendered TEXT NOT NULL,
    page_url TEXT,
    page_path TEXT NOT NULL,
    page_title TEXT,
    referrer TEXT,
    ip_address TEXT NOT NULL,
    ip_hash TEXT NOT NULL,
    user_agent TEXT,
    accept_language TEXT,
    submission_token TEXT,
    honeypot_value TEXT,
    filter_score INTEGER NOT NULL DEFAULT 0,
    filter_flags TEXT NOT NULL DEFAULT '[]',
    source_kind TEXT NOT NULL DEFAULT 'web_form',
    notes_internal TEXT NOT NULL DEFAULT '',
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_entries_status_created ON entries(status, created_utc DESC);
CREATE INDEX IF NOT EXISTS idx_entries_page_status_created ON entries(page_path, status, created_utc DESC);
CREATE INDEX IF NOT EXISTS idx_entries_ip_created ON entries(ip_address, created_utc DESC);

CREATE TABLE IF NOT EXISTS moderation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    event_utc TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_moderation_entry ON moderation_events(entry_id, event_utc DESC);

