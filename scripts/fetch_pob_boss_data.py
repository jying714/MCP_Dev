#!/usr/bin/env python3
import os
import re
import json
import requests
from datetime import datetime
from slpp import slpp as lua

# Source URLs
BASE_RAW        = "https://raw.githubusercontent.com/PathOfBuildingCommunity/PathOfBuilding-PoE2/dev/src/Data"
URL_BOSSES      = f"{BASE_RAW}/Bosses.lua"
URL_BOSS_SKILLS = f"{BASE_RAW}/BossSkills.lua"

DATA_DIR_RAW = os.path.join("data", "raw_bosses")
LATEST_DIR   = "data"

def fetch_and_snapshot():
    os.makedirs(DATA_DIR_RAW, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # --- Boss metadata parsing ---
    print("→ Fetching Bosses.lua…")
    resp = requests.get(URL_BOSSES, timeout=30)
    resp.raise_for_status()
    lua_text = resp.text

    # Extract bosses["Key"] = {...} blocks
    boss_pattern = re.compile(
        r'bosses\["(?P<key>[^"]+)"\]\s*=\s*(?P<table>\{.*?\})',
        re.DOTALL
    )
    bosses = {}
    for m in boss_pattern.finditer(lua_text):
        key = m.group("key")
        tbl = m.group("table")
        try:
            bosses[key] = lua.decode(tbl)
        except Exception as e:
            print(f"⚠️  Failed to decode boss {key}: {e}")

    # Save boss metadata JSON
    raw_bosses_path = os.path.join(DATA_DIR_RAW, f"bosses_{timestamp}.json")
    with open(raw_bosses_path, "w", encoding="utf-8") as f:
        json.dump(bosses, f, indent=2)
    with open(os.path.join(LATEST_DIR, "bosses.json"), "w", encoding="utf-8") as f:
        json.dump(bosses, f, indent=2)
    print(f"  • Boss metadata snapshot → raw_bosses/bosses_{timestamp}.json")

    # --- BossSkills parsing ---
    print("→ Fetching BossSkills.lua…")
    resp2 = requests.get(URL_BOSS_SKILLS, timeout=30)
    resp2.raise_for_status()
    skills_text = resp2.text

    # Extract the return { … } block
    m2 = re.search(r'return\s*(\{.*\})', skills_text, flags=re.DOTALL)
    if not m2:
        raise RuntimeError("Could not find top‑level table in BossSkills.lua")
    tbl2 = m2.group(1)

    try:
        skills_obj = lua.decode(tbl2)
    except Exception as e:
        print(f"⚠️  Failed to decode BossSkills.lua: {e}")
        skills_obj = {}

    # Save boss skills JSON
    raw_skills_path = os.path.join(DATA_DIR_RAW, f"boss_skills_{timestamp}.json")
    with open(raw_skills_path, "w", encoding="utf-8") as f:
        json.dump(skills_obj, f, indent=2)
    with open(os.path.join(LATEST_DIR, "boss_skills.json"), "w", encoding="utf-8") as f:
        json.dump(skills_obj, f, indent=2)
    print(f"  • BossSkills snapshot    → raw_bosses/boss_skills_{timestamp}.json")

    return bosses, skills_obj

if __name__ == "__main__":
    fetch_and_snapshot()
