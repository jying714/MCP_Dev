#!/usr/bin/env python3
import os
import json
import requests
from datetime import datetime
from slpp import slpp as lua

# Source URLs
BASE_RAW = "https://raw.githubusercontent.com/PathOfBuildingCommunity/PathOfBuilding-PoE2/dev/src/Data"
URL_BOSSES      = f"{BASE_RAW}/Bosses.lua"
URL_BOSS_SKILLS = f"{BASE_RAW}/BossSkills.lua"

DATA_DIR_RAW = os.path.join("data", "raw_bosses")
LATEST_DIR   = "data"

def fetch_and_snapshot():
    os.makedirs(DATA_DIR_RAW, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # Helper to fetch & parse a Lua file
    def fetch_lua(url, name):
        print(f"→ Fetching {name} from PoB repo…")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        pyobj = lua.decode(r.text)
        # write timestamped JSON
        with open(os.path.join(DATA_DIR_RAW, f"{name}_{timestamp}.json"), "w", encoding="utf-8") as f:
            json.dump(pyobj, f, indent=2)
        # overwrite “latest”
        with open(os.path.join(LATEST_DIR, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(pyobj, f, indent=2)
        print(f"  • {name}: snapshot → raw_bosses/{name}_{timestamp}.json")
        return pyobj

    bosses_data      = fetch_lua(URL_BOSSES,      "bosses")
    boss_skills_data = fetch_lua(URL_BOSS_SKILLS, "boss_skills")

    return bosses_data, boss_skills_data

if __name__ == "__main__":
    fetch_and_snapshot()
