-- migrations/012_parse_modifiers.sql

BEGIN;

/*
  Parsed modifiers table:
  - source_table: which ETL table the raw modifier came from
  - source_key:    the key (e.g. item_name, node_id, boss_id, gem_name) identifying the row
  - raw_modifier:  the original unparsed modifier text
  - stat_key:      the normalized stat identifier (e.g. "increased Fire Damage")
  - operator:      "+" or "-" indicating sign
  - magnitude_min: numeric minimum
  - magnitude_max: numeric maximum
  - unit:          e.g. "%", or NULL if none
  - tags:          reserved for future use (JSON text)
*/
DROP TABLE IF EXISTS mod_parsed;
CREATE TABLE mod_parsed (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  source_table    TEXT    NOT NULL,
  source_key      TEXT    NOT NULL,
  raw_modifier    TEXT    NOT NULL,
  stat_key        TEXT,
  operator        TEXT,
  magnitude_min   REAL,
  magnitude_max   REAL,
  unit            TEXT,
  tags            TEXT
);

-- Indexes to speed lookups by stat_key and by source_table
CREATE INDEX IF NOT EXISTS idx_mod_parsed_stat_key
  ON mod_parsed(stat_key);

CREATE INDEX IF NOT EXISTS idx_mod_parsed_source_table
  ON mod_parsed(source_table);

COMMIT;
