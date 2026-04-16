CREATE TABLE IF NOT EXISTS source_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_path TEXT NOT NULL,
  file_name TEXT NOT NULL,
  extension TEXT,
  file_hash TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  discovered_at TEXT NOT NULL,
  UNIQUE(source_path, file_hash)
);

CREATE TABLE IF NOT EXISTS processing_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file_id INTEGER NOT NULL,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  message TEXT,
  FOREIGN KEY(source_file_id) REFERENCES source_files(id)
);

CREATE TABLE IF NOT EXISTS interpreted_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file_id INTEGER NOT NULL,
  parser_type TEXT NOT NULL,
  confidence REAL NOT NULL,
  interpreted_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_file_id) REFERENCES source_files(id)
);

CREATE TABLE IF NOT EXISTS dataset_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file_id INTEGER NOT NULL,
  semver TEXT NOT NULL,
  normalized_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_file_id) REFERENCES source_files(id)
);

CREATE TABLE IF NOT EXISTS artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dataset_version_id INTEGER NOT NULL,
  artifact_type TEXT NOT NULL,
  artifact_path TEXT NOT NULL,
  checksum_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(dataset_version_id) REFERENCES dataset_versions(id)
);

CREATE TABLE IF NOT EXISTS event_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  processed_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  metadata_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  jti TEXT NOT NULL UNIQUE,
  username TEXT NOT NULL,
  role TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  used_at TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS revoked_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  jti TEXT NOT NULL UNIQUE,
  token_type TEXT NOT NULL,
  reason TEXT NOT NULL,
  expires_at TEXT,
  revoked_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(username);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_jti ON refresh_tokens(jti);
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_jti ON revoked_tokens(jti);
