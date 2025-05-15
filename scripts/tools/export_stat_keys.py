#!/usr/bin/env python3
"""
scripts/export_stat_keys.py

Extract every distinct stat key from your normalized tables and
write out a CSV skeleton for annotation.

Usage:
    python scripts/export_stat_keys.py
"""
import os
import sqlite3
import csv

# Path to your project’s SQLite store
DB_PATH = os.path.join("db", "passive_tree.db")

# Tables and their key columns to scan
TABLE_KEY_COLS = {
    "node_effects":                 "stat_key",
    "boss_skill_additional_stats":  "stat_key",
    "boss_skill_penetrations":      "pen_type",
    "gem_attributes":               "attr_key",
    "gem_additional_stats":         "stat_set_key",
    # Add more tables here as you normalize them (e.g., atlas_effects: "effect_key")
}

def main():
    # Connect to the DB and collect all unique keys
    conn = sqlite3.connect(DB_PATH)
    keys = set()
    for table, col in TABLE_KEY_COLS.items():
        try:
            cursor = conn.execute(f"SELECT DISTINCT {col} FROM {table};")
        except sqlite3.OperationalError as e:
            print(f"Warning: could not query {table}.{col}: {e}")
            continue
        for (val,) in cursor.fetchall():
            if val:
                keys.add(val)
    conn.close()

    # Ensure config directory exists
    os.makedirs("config", exist_ok=True)
    out_path = os.path.join("config", "stat_definitions_skeleton.csv")

    # Write CSV skeleton
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["stat_key", "unit", "description"])
        for key in sorted(keys):
            writer.writerow([key, "", ""])

    print(f"Exported {len(keys)} unique stat keys to {out_path}")

if __name__ == "__main__":
    main()
