#!/usr/bin/env python3
"""
Fetch all stat‑description Lua files listed in stats_manifest.json
and snapshot them to data/raw_stats with a timestamp.
"""
import json
import requests
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from requests.exceptions import HTTPError

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

# ── Resilient GET with exponential backoff ───────────────────────────────────
def safe_get(url, **kwargs):
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        resp = requests.get(url, **kwargs)
        if resp.status_code == 429:
            wait = 2 ** attempt
            logger.warning(f"Rate limited fetching {url}, retrying in {wait}s (attempt {attempt}/{max_attempts})")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    raise HTTPError(f"Rate limited: failed to fetch {url} after {max_attempts} attempts")

# ── Helper: list all specific skill files via GitHub API ──────────────────────
def list_specific_files():
    api_url = (
        "https://api.github.com/repos/"
        "PathOfBuildingCommunity/PathOfBuilding-PoE2/contents/"
        "src/Data/StatDescriptions/Specific_Skill_Stat_Descriptions?ref=dev"
    )
    resp = safe_get(api_url, timeout=30)
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
        tmpl = entry["urlTemplate"]
        for fname in list_specific_files():
            url = tmpl.replace("{filename}", fname)
            resp = safe_get(url, timeout=30)
            dest = RAW_DIR / f"{fname}_{timestamp}.lua"
            dest.write_text(resp.text, encoding="utf-8")
            logger.info(f"Fetched {fname} → {dest}")
    else:
        url = entry.get("url")
        resp = safe_get(url, timeout=30)
        fname = path.replace("/", "_")
        dest = RAW_DIR / f"{fname}_{timestamp}.lua"
        dest.write_text(resp.text, encoding="utf-8")
        logger.info(f"Fetched {path} → {dest}")

print("All stat files fetched and snapshot to data/raw_stats/")
