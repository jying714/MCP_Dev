#!/usr/bin/env python3
import requests
import json
import logging
from pathlib import Path
from datetime import datetime

# === Path setup ===
HERE         = Path(__file__).parent
PROJECT_ROOT = HERE.parent
DATA_DIR     = PROJECT_ROOT / "data"
RAW_DIR      = DATA_DIR / "raw_trees"
LOG_DIR      = PROJECT_ROOT / "logs" / "fetch_and_load_tree401"

# Ensure directories exist
for d in (DATA_DIR, RAW_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# === Logging Setup ===
LOG_FILE = LOG_DIR / "fetch_and_load_tree401.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
URL = "https://assets-ng.maxroll.gg/poe2planner/game/tree401.json?0dce6a5f"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
}

def main():
    try:
        logger.info(f"Fetching {URL}")
        resp = requests.get(URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        # 1) Prepare timestamp and raw_trees dir
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        raw_path = RAW_DIR / f"{timestamp}.json"

        # 2) Write the versioned snapshot
        with raw_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info(f"Wrote raw snapshot to {raw_path}")

        # 3) Overwrite the latest file for backward compatibility
        latest = DATA_DIR / "tree401.json"
        with latest.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info(f"Updated latest JSON at {latest}")

        # 4) Print only the raw snapshot path for downstream capture
        print(str(raw_path))

    except requests.RequestException as e:
        logger.error(f"Error fetching JSON: {e}")
        print(f"❌ Error fetching JSON: {e}")
        exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"❌ Unexpected error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
