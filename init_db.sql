CREATE TABLE IF NOT EXISTS messages (
    sender_id TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS subscribers (
    id TEXT,
    init_datetime DATETIME,
    UNIQUE(id)
);

CREATE TABLE IF NOT EXISTS senders (
    id TEXT,
    init_datetime DATETIME,
    UNIQUE(id)
);
