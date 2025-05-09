-- 006_boss_skill_norm.sql
-- Migration: normalize boss_skills into core + multipliers + penetrations + additional_stats

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- 1. Create core boss_skills table
CREATE TABLE IF NOT EXISTS boss_skills_core (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  boss_id           INTEGER NOT NULL
                      REFERENCES bosses(id)
                      ON DELETE CASCADE,
  skill_key         TEXT    NOT NULL,
  name              TEXT,
  damage_type       TEXT,
  base_speed        REAL,
  crit_chance       REAL    DEFAULT 0,
  uber_multiplier   REAL,
  uber_speed        REAL,
  earlier_uber_flag BOOLEAN DEFAULT 0,
  tooltip           TEXT,
  UNIQUE (boss_id, skill_key)
);

-- 2. Create multipliers table
CREATE TABLE IF NOT EXISTS boss_skill_multipliers (
  skill_id    INTEGER NOT NULL
                 REFERENCES boss_skills_core(id)
                 ON DELETE CASCADE,
  damage_type TEXT    NOT NULL,
  base_value  REAL    NOT NULL,
  ratio_value REAL    NOT NULL,
  PRIMARY KEY (skill_id, damage_type)
);

-- 3. Create penetrations table
CREATE TABLE IF NOT EXISTS boss_skill_penetrations (
  skill_id  INTEGER NOT NULL
               REFERENCES boss_skills_core(id)
               ON DELETE CASCADE,
  pen_type  TEXT    NOT NULL,
  base_pen  REAL    DEFAULT 0,
  uber_pen  REAL    DEFAULT 0,
  PRIMARY KEY (skill_id, pen_type)
);

-- 4. Create additional stats table
CREATE TABLE IF NOT EXISTS boss_skill_additional_stats (
  skill_id   INTEGER NOT NULL
                 REFERENCES boss_skills_core(id)
                 ON DELETE CASCADE,
  phase      TEXT    NOT NULL,      -- 'base' or 'uber'
  stat_key   TEXT    NOT NULL,
  stat_value REAL,
  is_flag    BOOLEAN DEFAULT 0,
  PRIMARY KEY (skill_id, phase, stat_key)
);


COMMIT;
PRAGMA foreign_keys = ON;
