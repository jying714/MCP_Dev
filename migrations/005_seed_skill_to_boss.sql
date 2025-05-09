-- 005_seed_skill_to_boss.sql

-- 1) Ensure the mapping table exists
CREATE TABLE IF NOT EXISTS skill_to_boss (
  skill_key_pattern TEXT PRIMARY KEY,
  boss_key          TEXT NOT NULL
);

-- 2) Seed your known overrides
INSERT OR REPLACE INTO skill_to_boss(skill_key_pattern, boss_key) VALUES
  ('Eater Beam',  'EaterOfWorlds'),
  ('Exarch Ball', 'SearingExarch');
