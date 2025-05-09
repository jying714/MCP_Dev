#!/usr/bin/env python3
import os
import sys
import json
import argparse
from datetime import datetime
import sqlite3
from pathlib import Path

# === Constants ===
SCRIPT_DIR = Path(__file__).parent
DB_PATH    = SCRIPT_DIR.parent / "db" / "passive_tree.db"

def parse_args():
    p = argparse.ArgumentParser(
        description="Register a new passive-tree version and store its raw JSON"
    )
    p.add_argument(
        "--json-file", "-j",
        required=True,
        help="Path to the raw JSON file (e.g. data/tree401.json)"
    )
    p.add_argument(
        "--timestamp", "-t",
        help=(
            "Timestamp tag for this version "
            "(default: UTC now in YYYYMMDDTHHMMSSZ)"
        )
    )
    return p.parse_args()

def main():
    args = parse_args()

    # 1) Read the raw JSON
    json_path = Path(args.json_file)
    if not json_path.is_file():
        print(f"ERROR: JSON file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    raw_json = json_path.read_text(encoding="utf-8")
    parsed   = json.loads(raw_json)

    # 2) Determine the version_tag
    if args.timestamp:
        version_tag = args.timestamp
    else:
        version_tag = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # 3) Open the SQLite database
    conn = sqlite3.connect(str(DB_PATH))
    cur  = conn.cursor()

    # 4) Insert into tree_versions
    fetched_at = datetime.utcnow().isoformat(sep=' ')
    source_url = str(json_path)
    cur.execute(
        "INSERT INTO tree_versions (version_tag, fetched_at, source_url) VALUES (?, ?, ?);",
        (version_tag, fetched_at, source_url)
    )
    version_id = cur.lastrowid

    # 5) Insert into raw_trees
    cur.execute(
        "INSERT INTO raw_trees (version_id, raw_json) VALUES (?, ?);",
        (version_id, raw_json)
    )

    conn.commit()
    conn.close()

    # 6) Print the new version_id
    print(version_id)

if __name__ == "__main__":
    main()
