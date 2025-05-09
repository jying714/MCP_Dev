-- 008_optimizations.sql
BEGIN;

-- 1) Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_boss_skill_mult_type
  ON boss_skill_multipliers(damage_type);

CREATE INDEX IF NOT EXISTS idx_gem_tags_tag
  ON gem_tags(tag);

CREATE INDEX IF NOT EXISTS idx_gem_attrs_key
  ON gem_attributes(attr_key);

-- 2) Stat catalog table
CREATE TABLE IF NOT EXISTS stat_definitions (
  stat_key    TEXT PRIMARY KEY,
  unit        TEXT,
  description TEXT
);

COMMIT;
