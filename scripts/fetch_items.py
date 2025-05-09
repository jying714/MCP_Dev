#!/usr/bin/env python3
import requests
from pathlib import Path

# Use ASCII hyphens here
ITEMS_URL   = "https://assets-ng.maxroll.gg/poe2planner/game/items.json"
UNIQUES_URL = "https://assets-ng.maxroll.gg/poe2planner/game/uniques.json"

def fetch_and_save(url, dest_path):
    print(f"Fetching {url} …")
    resp = requests.get(url, headers={"User-Agent": "MCP-Dev-Bot/1.0"})
    resp.raise_for_status()

    dest = Path(__file__).parent.parent / "data" / dest_path
    dest.parent.mkdir(exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(resp.text)
    print(f"Saved to {dest}")

if __name__ == "__main__":
    fetch_and_save(ITEMS_URL,   "items.json")
    fetch_and_save(UNIQUES_URL, "uniques.json")
