CREATE TABLE IF NOT EXISTS opens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tracking_id TEXT NOT NULL,
  recipient TEXT,
  opened_at TEXT NOT NULL DEFAULT (datetime('now')),
  ip TEXT,
  user_agent TEXT,
  country TEXT,
  city TEXT
);

CREATE INDEX IF NOT EXISTS idx_opens_tracking_id ON opens(tracking_id);
CREATE INDEX IF NOT EXISTS idx_opens_recipient ON opens(recipient);
CREATE INDEX IF NOT EXISTS idx_opens_opened_at ON opens(opened_at);
