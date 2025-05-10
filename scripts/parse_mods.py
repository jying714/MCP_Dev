#!/usr/bin/env python3
import sqlite3
import re
from pathlib import Path

# Path to the SQLite database
db_path = Path(__file__).parent.parent / "db" / "passive_tree.db"

# Pattern to remove any {tags:...} or {variant:...} markers
CLEANER = re.compile(r"\{[^}]+\}")

# Regex to match optional sign, number, optional range, and the stat key
MOD_PATTERN = re.compile(
    r"^(?P<sign>[+\-]?)\s*"
    r"(?P<min>\d+(?:\.\d+)?)"
    r"(?:[-–](?P<max>\d+(?:\.\d+)?))?"
    r"\s*(?P<key>.+)$"
)

def parse_modifier(raw: str):
    """Parse a raw modifier into (stat_key, min_value, max_value, is_range)."""
    text = CLEANER.sub("", raw).strip()
    m = MOD_PATTERN.match(text)
    if not m:
        # No numeric content — keep text verbatim
        return text, None, None, False

    sign = m.group("sign") or "+"
    minv = float(m.group("min"))
    maxv = float(m.group("max")) if m.group("max") else minv

    # Ensure minv <= maxv
    if maxv < minv:
        minv, maxv = maxv, minv

    # Apply negative sign
    if sign == "-":
        minv = -minv
        maxv = -maxv if m.group("max") else minv

    is_range = (m.group("max") is not None) and (minv != maxv)
    stat_key = m.group("key").strip()
    return stat_key, minv, maxv, is_range

def insert_ignore(cur, table, columns, values):
    """Helper to perform INSERT OR IGNORE into a table."""
    cols = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders});"
    cur.execute(sql, values)


def main():
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Clear existing parsed data
    cur.execute("DELETE FROM mod_parsed;")

    # --- 1) Parse unique_mods ---
    rows = cur.execute(
        "SELECT item_name, version_id, modifier FROM unique_mods;"
    ).fetchall()
    for item_name, version_id, raw in rows:
        stat_key, mn, mx, rng = parse_modifier(raw)
        insert_ignore(cur, 'mod_parsed',
                      ['item_name', 'version_id', 'stat_key', 'min_value', 'max_value', 'is_range'],
                      (item_name, version_id, stat_key, mn, mx, int(rng)))

    # --- 2) Parse node_effects ---
    rows = cur.execute(
        "SELECT node_id, stat_key, value, version_id FROM node_effects;"
    ).fetchall()
    for node_id, stat, val, version_id in rows:
        raw = f"{val} {stat}"
        stat_key, mn, mx, rng = parse_modifier(raw)
        insert_ignore(cur, 'mod_parsed',
                      ['item_name', 'version_id', 'stat_key', 'min_value', 'max_value', 'is_range'],
                      (str(node_id), version_id, stat_key, mn, mx, int(rng)))

    # --- 3) Parse boss_skill_additional_stats with real version_id ---
    boss_rows = cur.execute(
        """
        SELECT s.skill_id, s.stat_key, s.stat_value, b.version_id
        FROM boss_skill_additional_stats s
        JOIN boss_skills_core k ON s.skill_id = k.id
        JOIN bosses b ON k.boss_id = b.id;
        """
    ).fetchall()
    for skill_id, stat, val, version_id in boss_rows:
        raw = f"{val} {stat}"
        stat_key, mn, mx, rng = parse_modifier(raw)
        insert_ignore(cur, 'mod_parsed',
                      ['item_name', 'version_id', 'stat_key', 'min_value', 'max_value', 'is_range'],
                      (str(skill_id), version_id, stat_key, mn, mx, int(rng)))

    # --- 4) Parse gem_additional_stats ---
    gem_rows = cur.execute(
        "SELECT gem_name, version_id, stat_set_key, stat_set_value FROM gem_additional_stats;"
    ).fetchall()
    for gem_name, version_id, key, val in gem_rows:
        raw = f"{val} {key}"
        stat_key, mn, mx, rng = parse_modifier(raw)
        insert_ignore(cur, 'mod_parsed',
                      ['item_name', 'version_id', 'stat_key', 'min_value', 'max_value', 'is_range'],
                      (gem_name, version_id, stat_key, mn, mx, int(rng)))

    conn.commit()
    conn.close()
    print("✅ Parsed all modifiers into mod_parsed")

if __name__ == "__main__":
    main()