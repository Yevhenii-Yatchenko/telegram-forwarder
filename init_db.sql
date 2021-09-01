CREATE TABLE IF NOT EXISTS messages (
    sender_id TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS subscribers (
    id TEXT,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    init_datetime DATETIME,
    UNIQUE(id)
);

CREATE TABLE IF NOT EXISTS senders (
    id TEXT,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    init_datetime DATETIME,
    UNIQUE(id)
);
