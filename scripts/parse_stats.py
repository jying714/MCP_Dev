#!/usr/bin/env python3
"""
Parse + load ALL stat‑description Lua snapshots into SQLite,
including Specific_Skill_Stat_Descriptions overrides,
and automatically record each run in tree_versions.
"""
import sqlite3
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from slpp import slpp

# ── Paths & Setup ────────────────────────────────────────────────────────────
HERE         = Path(__file__).parent
PROJECT_ROOT = HERE.parent
RAW_DIR      = PROJECT_ROOT / "data" / "raw_stats"
DB_PATH      = PROJECT_ROOT / "db" / "passive_tree.db"
LOG_DIR      = PROJECT_ROOT / "logs" / "parse_stats"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "parse_stats.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

INSERT_DEF_SQL = """
INSERT OR REPLACE INTO stat_definitions
  (stat_key, unit, description, param_keys, category, version_id)
VALUES (?, ?, ?, ?, ?, ?);
"""

INSERT_OVR_SQL = """
INSERT OR REPLACE INTO stat_overrides
  (stat_key, skill_key, override_desc, override_params, override_limits, version_id)
VALUES (?, ?, ?, ?, ?, ?);
"""

GENERIC_FILES = {
    'stat_descriptions':                    'generic',
    'passive_skill_stat_descriptions':      'passive',
    'passive_skill_aura_stat_descriptions': 'passive_aura',
    'active_skill_gem_stat_descriptions':   'gem',
    'gem_stat_descriptions':                'gem',
    'advanced_mod_stat_descriptions':       'mod',
    'meta_gem_stat_descriptions':           'gem_meta',
    'monster_stat_descriptions':            'monster',
    'skill_stat_descriptions':              'skill',
    'utility_flask_buff_stat_descriptions': 'flask',
}

_timestamp_re = re.compile(r'_\d{8}T\d{6}Z\.lua$')

def base_name(filename: str) -> str:
    """
    Normalize a raw_stats filename to one of the GENERIC_FILES keys
    if it ends with that key, otherwise return the trimmed filename.
    """
    no_ts = _timestamp_re.sub('', filename)
    no_ext = no_ts[:-4] if no_ts.lower().endswith('.lua') else no_ts
    for key in GENERIC_FILES:
        if no_ext.endswith(key):
            return key
    return no_ext

def decode_lua(path: Path) -> dict:
    """
    Strip comments and the leading 'return ...;' wrapper, then decode via SLPP.
    Returns a dict or empty dict on failure.
    """
    txt = path.read_text(encoding="utf-8")
    lines = txt.splitlines()
    body_lines = [ln for ln in lines if not ln.strip().startswith("--")]
    body = "\n".join(body_lines).strip()
    if body.startswith("return "):
        body = body[len("return "):]
    if body.endswith(";"):
        body = body[:-1]
    try:
        data = slpp.decode(body)
    except Exception as e:
        logger.warning(f"Skipping {path.name}: failed to decode ({e})")
        return {}
    return data if isinstance(data, dict) else {}

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # 1) Record a new version
        version_tag = f"stats_import_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
        fetched_at  = datetime.utcnow()
        source_url  = 'parse_stats.py'
        cur.execute(
            "INSERT INTO tree_versions(version_tag, fetched_at, source_url) VALUES (?,?,?)",
            (version_tag, fetched_at, source_url)
        )
        version_id = cur.lastrowid

        # 2) Parse & upsert each snapshot
        for lua_file in sorted(RAW_DIR.glob("*.lua")):
            name = base_name(lua_file.name)
            data = decode_lua(lua_file)
            if not data:
                continue

            if name in GENERIC_FILES:
                category = GENERIC_FILES[name]
                for raw_key, entry in data.items():
                    stat_key = str(raw_key)
                    if isinstance(entry, dict):
                        unit   = entry.get("statKeyType", "STRING")
                        stats  = entry.get("stats", [])
                        desc   = "\n".join(str(s) for s in stats)
                        params = entry.get(1, []) or []
                    else:
                        unit, desc, params = "STRING", str(entry), []
                    cur.execute(INSERT_DEF_SQL, (
                        stat_key, unit, desc, json.dumps(params),
                        category, version_id
                    ))
                logger.info(f"Loaded definitions from {name}")
            else:
                for raw_key, entry in data.items():
                    stat_key = str(raw_key)
                    if isinstance(entry, dict):
                        stats  = entry.get("stats", [])
                        desc   = "\n".join(str(s) for s in stats)
                        params = entry.get(1, []) or []
                        limits = entry.get("limit", {}) or {}
                    else:
                        desc, params, limits = str(entry), [], {}
                    skill_key = stat_key.split("_", 1)[0]
                    cur.execute(INSERT_OVR_SQL, (
                        stat_key, skill_key, desc,
                        json.dumps(params), json.dumps(limits),
                        version_id
                    ))
                logger.info(f"Loaded overrides from {name}")

        conn.commit()
        print("✅ Parsed and loaded all stat descriptions (generic + overrides).")
    except Exception:
        conn.rollback()
        logger.exception("parse_stats.py failed")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
