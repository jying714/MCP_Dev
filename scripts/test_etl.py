# scripts/test_etl.py
#!/usr/bin/env python3
"""
Standalone ETL sanity check for MCP passive‑tree load.
Run with:
    python scripts/test_etl.py
(no CLI args required)
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "passive_tree.db"

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Latest version
    cur.execute("SELECT MAX(version_id) FROM tree_versions;")
    vid = cur.fetchone()[0]
    print(f"✅ Latest version_id: {vid}\n")

    checks = [
        ("raw_trees     ", f"SELECT COUNT(*) FROM raw_trees WHERE version_id = {vid}"),
        ("passive_nodes ", f"SELECT COUNT(*) FROM passive_nodes WHERE version_id = {vid}"),
        ("node_edges    ", f"SELECT COUNT(*) FROM node_edges WHERE version_id = {vid}"),
        ("node_effects  ", f"SELECT COUNT(*) FROM node_effects WHERE version_id = {vid}"),
        ("starting_nodes", f"SELECT COUNT(*) FROM starting_nodes WHERE version_id = {vid}"),
        ("ascendancy_nodes", f"SELECT COUNT(*) FROM ascendancy_nodes WHERE version_id = (SELECT MAX(version_id) FROM ascendancy_versions)"),
        ("node_errors   ", f"SELECT COUNT(*) FROM node_errors WHERE version_id = {vid}"),
        ("edge_errors   ", f"SELECT COUNT(*) FROM edge_errors WHERE version_id = {vid}"),
    ]

    for name, sql in checks:
        cur.execute(sql)
        count = cur.fetchone()[0]
        print(f"{name}: {count}")

    # Sample rows
    print("\n-- Sample passive_nodes rows --")
    cur.execute(f"PRAGMA table_info(passive_nodes)")
    cols = [c[1] for c in cur.fetchall()]
    cur.execute(f"SELECT * FROM passive_nodes WHERE version_id = {vid} LIMIT 5")
    rows = cur.fetchall()
    if rows:
        print(" | ".join(cols))
        for r in rows:
            print(" | ".join(str(x) for x in r))
    else:
        print("No rows found in passive_nodes for this version—ETL may have failed.")

    conn.close()

if __name__ == '__main__':
    main()
