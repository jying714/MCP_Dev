-- migrations/009_parse_mods.sql
BEGIN;

-- Parsed modifiers table
CREATE TABLE IF NOT EXISTS mod_parsed (
  item_name    TEXT    NOT NULL,
  version_id   INTEGER NOT NULL REFERENCES item_versions(version_id),
  stat_key     TEXT    NOT NULL,
  min_value    REAL,
  max_value    REAL,
  is_range     BOOLEAN DEFAULT 0,
  PRIMARY KEY (item_name, version_id, stat_key)
);

COMMIT;
