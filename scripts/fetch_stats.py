#!/usr/bin/env python3
"""
Fetch all stat‑description Lua files listed in stats_manifest.json
and snapshot them to data/raw_stats with a timestamp.
"""
import json
import requests
import logging
import sys
from pathlib import Path
from datetime import datetime

# ── Paths & Setup ────────────────────────────────────────────────────────────
HERE         = Path(__file__).parent
PROJECT_ROOT = HERE.parent
RAW_DIR      = PROJECT_ROOT / "data" / "raw_stats"
MANIFEST     = PROJECT_ROOT / "stats_manifest.json"
LOG_DIR      = PROJECT_ROOT / "logs" / "fetch_stats"

for d in (RAW_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "fetch_stats.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Load Manifest ────────────────────────────────────────────────────────────
with MANIFEST.open(encoding="utf-8") as f:
    manifest = json.load(f)

# Timestamp for snapshot files
timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

# ── Helper: list all specific skill files via GitHub API ──────────────────────
def list_specific_files():
    api_url = (
        "https://api.github.com/repos/"
        "PathOfBuildingCommunity/PathOfBuilding-PoE2/contents/"
        "src/Data/StatDescriptions/Specific_Skill_Stat_Descriptions?ref=dev"
    )
    resp = requests.get(api_url, timeout=30)
    resp.raise_for_status()
    entries = resp.json()
    return [
        e["name"]
        for e in entries
        if e.get("type") == "file" and e.get("name", "").endswith(".lua")
    ]

# ── Fetch Loop ───────────────────────────────────────────────────────────────
for entry in manifest.get("files", []):
    path = entry.get("path", "")
    if "*" in path:
        # Wildcard → fetch each specific‑skill file
        tmpl = entry["urlTemplate"]
        for fname in list_specific_files():
            url = tmpl.replace("{filename}", fname)
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            dest = RAW_DIR / f"{fname}_{timestamp}.lua"
            dest.write_text(resp.text, encoding="utf-8")
            logger.info(f"Fetched {fname} → {dest}")
    else:
        # Single file entry
        url = entry.get("url")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        # flatten path to filename
        fname = path.replace("/", "_")
        dest = RAW_DIR / f"{fname}_{timestamp}.lua"
        dest.write_text(resp.text, encoding="utf-8")
        logger.info(f"Fetched {path} → {dest}")

print("All stat files fetched and snapshot to data/raw_stats/")
