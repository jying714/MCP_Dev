-- Add JSON params, category, and version tracking to stat_definitions
ALTER TABLE stat_definitions
  ADD COLUMN param_keys   TEXT    NOT NULL DEFAULT '[]';

ALTER TABLE stat_definitions
  ADD COLUMN category     TEXT    DEFAULT 'generic';

ALTER TABLE stat_definitions
  ADD COLUMN version_id   INTEGER REFERENCES tree_versions(version_id);
