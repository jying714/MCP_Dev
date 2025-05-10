-- migrations/012_parse_modifiers.sql

BEGIN;

-- Drop any existing mod_parsed table to replace with the updated schema
DROP TABLE IF EXISTS mod_parsed;

-- Create the new mod_parsed table with structured columns
CREATE TABLE mod_parsed (
  item_name    TEXT    NOT NULL,
  version_id   INTEGER NOT NULL REFERENCES item_versions(version_id),
  stat_key     TEXT    NOT NULL,
  min_value    REAL,
  max_value    REAL,
  is_range     BOOLEAN DEFAULT 0,
  PRIMARY KEY (item_name, version_id, stat_key)
);

-- Optional indexes to speed common lookups
CREATE INDEX IF NOT EXISTS idx_mod_parsed_item
  ON mod_parsed(item_name);

CREATE INDEX IF NOT EXISTS idx_mod_parsed_version
  ON mod_parsed(version_id);

COMMIT;
