-- migrations/20250513_add_stat_tables.sql

BEGIN;

/* 1) Generic stat definitions */
CREATE TABLE IF NOT EXISTS stat_definitions (
  stat_key       TEXT    PRIMARY KEY,
  description    TEXT    NOT NULL,          -- template string with placeholders
  param_keys     TEXT    NOT NULL,          -- JSON‑encoded array of parameter names
  category       TEXT    NOT NULL,          -- e.g. 'generic','gem','mod','flask'
  version_id     INTEGER NOT NULL REFERENCES tree_versions(version_id)
);

/* 2) Per‑skill stat overrides */
CREATE TABLE IF NOT EXISTS stat_overrides (
  stat_key           TEXT    NOT NULL,
  skill_key          TEXT    NOT NULL,
  override_desc      TEXT    NOT NULL,      -- template string
  override_params    TEXT    NOT NULL,      -- JSON‑encoded array
  version_id         INTEGER NOT NULL REFERENCES tree_versions(version_id),
  PRIMARY KEY (stat_key, skill_key)
);

COMMIT;
