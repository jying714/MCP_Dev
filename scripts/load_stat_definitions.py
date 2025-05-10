#!/usr/bin/env python3
import sqlite3
import csv
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "passive_tree.db"
CSV_PATH = Path(__file__).parent.parent / "config" / "stat_definitions.csv"

# Map each table to the column holding the key to catalog
TABLE_KEY_COLS = {
    "boss_skill_additional_stats":  "stat_key",
    "boss_skill_penetrations":      "pen_type",
    "gem_attributes":               "attr_key",
    "gem_additional_stats":         "stat_set_key",
}

def seed_stat_keys(conn):
    keys = set()
    for tbl, col in TABLE_KEY_COLS.items():
        for row in conn.execute(f"SELECT DISTINCT {col} FROM {tbl};"):
            key = row[0]
            if key:
                keys.add(key)
    for key in sorted(keys):
        conn.execute(
            "INSERT OR IGNORE INTO stat_definitions(stat_key) VALUES (?);",
            (key,)
        )
    return len(keys)

def enrich_stat_definitions(conn):
    if not CSV_PATH.exists():
        print(f"❌ Missing CSV at {CSV_PATH}")
        return 0

    count = 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stat_key    = row["stat_key"].strip()
            unit        = row.get("unit", "").strip()
            description = row.get("description", "").strip()
            if stat_key:
                cur = conn.execute("""
                    UPDATE stat_definitions
                       SET unit = ?, description = ?
                     WHERE stat_key = ?
                """, (unit, description, stat_key))
                if cur.rowcount:
                    count += 1
    return count

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        seeded = seed_stat_keys(conn)
        enriched = enrich_stat_definitions(conn)
        conn.commit()
        print(f"✅ Seeded {seeded} stat_definitions keys")
        print(f"✅ Enriched {enriched} stat_definitions with metadata")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
