-- migrations/011_fix_gem_view.sql
BEGIN;

DROP VIEW IF EXISTS vw_gems_projectile;

CREATE VIEW vw_gems_projectile AS
SELECT
  gc.gem_name,
  gc.name           AS display_name,
  sd.unit           AS unit,
  sd.description    AS description
FROM gems_core gc
JOIN gem_tags gt
  ON gt.gem_name = gc.gem_name
 AND gt.version_id = gc.version_id
JOIN stat_definitions sd
  ON sd.stat_key = 'tags'
WHERE gt.tag = 'projectile';

COMMIT;
