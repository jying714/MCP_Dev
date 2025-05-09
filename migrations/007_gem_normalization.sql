-- 007_gem_normalization.sql
-- Migration: normalize gems into core, tags, attributes, and additional stats

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- 1) Core table for top‑level gem fields
CREATE TABLE IF NOT EXISTS gems_core (
  gem_name          TEXT    NOT NULL,
  version_id        INTEGER NOT NULL REFERENCES item_versions(version_id),
  name              TEXT,
  base_type_name    TEXT,
  granted_effect_id TEXT,
  variant_id        TEXT,
  support_flag      BOOLEAN DEFAULT 0,
  PRIMARY KEY (gem_name, version_id)
);

-- 2) Tags e.g. 'spell', 'area', 'cold', 'nova'
CREATE TABLE IF NOT EXISTS gem_tags (
  gem_name   TEXT    NOT NULL,
  version_id INTEGER NOT NULL,
  tag        TEXT    NOT NULL,
  PRIMARY KEY (gem_name, version_id, tag),
  FOREIGN KEY (gem_name, version_id) REFERENCES gems_core(gem_name, version_id)
);

-- 3) Attributes for boolean/numeric fields like intelligence, duration, attack, etc.
CREATE TABLE IF NOT EXISTS gem_attributes (
  gem_name   TEXT    NOT NULL,
  version_id INTEGER NOT NULL,
  attr_key   TEXT    NOT NULL,
  attr_value TEXT,   -- store as TEXT since some values are 'true' / 'false' or numbers
  PRIMARY KEY (gem_name, version_id, attr_key),
  FOREIGN KEY (gem_name, version_id) REFERENCES gems_core(gem_name, version_id)
);

-- 4) AdditionalStatSets (e.g. additionalStatSet1, additionalStatSet2, …)
CREATE TABLE IF NOT EXISTS gem_additional_stats (
  gem_name      TEXT    NOT NULL,
  version_id    INTEGER NOT NULL,
  stat_set_key  TEXT    NOT NULL,  -- e.g. "additionalStatSet1"
  stat_set_value TEXT,              -- e.g. "\"IceNovaPlayerOnFrostbolt\""
  PRIMARY KEY (gem_name, version_id, stat_set_key),
  FOREIGN KEY (gem_name, version_id) REFERENCES gems_core(gem_name, version_id)
);

COMMIT;
PRAGMA foreign_keys = ON;
