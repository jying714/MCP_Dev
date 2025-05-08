# scripts/FetchAndLoadTree401.py
#!/usr/bin/env python3
import requests
import json
import logging
from pathlib import Path

# === Path setup ===
HERE         = Path(__file__).parent
PROJECT_ROOT = HERE.parent
DATA_DIR     = PROJECT_ROOT / "data"
LOG_DIR      = PROJECT_ROOT / "logs" / "fetch_and_load_tree401"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

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
    out_file = DATA_DIR / "tree401.json"
    try:
        logger.info(f"Fetching {URL}")
        resp = requests.get(URL, headers=HEADERS)
        resp.raise_for_status()
        payload = resp.json()

        with out_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved tree401.json to {out_file}")
        print(f"✅ tree401.json saved to {out_file}")
    except requests.RequestException as e:
        logger.error(f"Error fetching JSON: {e}")
        print(f"❌ Error fetching JSON: {e}")
        exit(1)

if __name__ == "__main__":
    main()
