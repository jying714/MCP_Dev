-- migrations/010_views.sql
BEGIN;

-- 1) View: Boss Fire Penetration with human‑readable units & descriptions
CREATE VIEW IF NOT EXISTS vw_boss_fire_penetration AS
SELECT
  b.id           AS skill_id,
  b.name         AS skill_name,
  p.base_pen     AS base_penetration,
  p.uber_pen     AS uber_penetration,
  sd.unit        AS unit,
  sd.description AS description
FROM boss_skills_core b
JOIN boss_skill_penetrations p
  ON p.skill_id = b.id
JOIN stat_definitions sd
  ON sd.stat_key = p.pen_type
WHERE p.pen_type = 'FirePen';

-- 2) View: Gems by Tag (example: projectile support gems)
CREATE VIEW IF NOT EXISTS vw_gems_projectile AS
SELECT
  g.gem_name,
  gc.name           AS display_name,
  sd.unit           AS unit,
  sd.description    AS description
FROM gems_core gc
JOIN gem_tags gt
  ON gt.gem_name = gc.gem_name AND gt.version_id = gc.version_id
JOIN stat_definitions sd
  ON sd.stat_key = 'tags'               -- describing the tags column
WHERE gt.tag = 'projectile';

COMMIT;
