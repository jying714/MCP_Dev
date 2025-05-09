#!/usr/bin/env python3
import os
import sys
import json
import argparse
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Table, Column, Integer, String, Text, MetaData, DateTime, ForeignKey

def parse_args():
    p = argparse.ArgumentParser(
        description="Register a new passive-tree version and store its raw JSON"
    )
    p.add_argument("--json-file", required=True,
                   help="Path to the raw JSON file (e.g. data/raw_trees/20250508T133256Z.json)")
    p.add_argument("--timestamp", required=True,
                   help="Timestamp tag for this version (e.g. 20250508T133256Z)")
    p.add_argument("--return-version-id", action="store_true",
                   help="Print the newly inserted version_id to stdout")
    return p.parse_args()

def main():
    args = parse_args()

    # Read the raw JSON
    with open(args.json_file, "r", encoding="utf-8") as f:
        raw_json = json.load(f)

    # Get DB URL from environment
    db_url = os.environ.get("DB_URL")
    if not db_url:
        print("ERROR: DB_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Create SQLAlchemy engine
    engine = sa.create_engine(db_url)
    metadata = MetaData()

    # Define tables matching your schema
    tree_versions = Table(
        "tree_versions", metadata,
        Column("version_id", Integer, primary_key=True, autoincrement=True),
        Column("version_tag", String, nullable=False, unique=True),
        Column("fetched_at", DateTime, nullable=False),
        Column("source_url", String, nullable=True),
    )
    raw_trees = Table(
        "raw_trees", metadata,
        Column("version_id", Integer, ForeignKey("tree_versions.version_id", ondelete="CASCADE"), primary_key=True),
        Column("raw_json", Text, nullable=False),
    )

    # Ensure tables exist (no-op if already in DB)
    metadata.create_all(engine)

    # Insert new version + raw JSON
    with engine.begin() as conn:
        now = datetime.utcnow()
        result = conn.execute(
            tree_versions.insert().values(
                version_tag=args.timestamp,
                fetched_at=now,
                source_url=args.json_file
            )
        )
        version_id = result.inserted_primary_key[0]

        conn.execute(
            raw_trees.insert().values(
                version_id=version_id,
                raw_json=json.dumps(raw_json)
            )
        )

    if args.return_version_id:
        print(version_id)

if __name__ == "__main__":
    main()
