#!/usr/bin/env python3
import requests
import re
import json
import logging
from collections import defaultdict
from pathlib import Path
from datetime import datetime

# === Paths ===
HERE = Path(__file__).parent
ROOT = HERE.parent
DATA_DIR = ROOT / "data" / "pob"
LOG_DIR = ROOT / "logs" / "fetch_pob_data"
for d in (DATA_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# === Logging ===
LOG_FILE = LOG_DIR / "fetch_pob_data.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# GitHub repo info
REPO_API = "https://api.github.com/repos/PathOfBuildingCommunity/PathOfBuilding-PoE2/contents"
BRANCH = "dev"

# Categories and where to save
CATEGORIES = {
    "uniques": DATA_DIR / "uniques.json",
    "bases":   DATA_DIR / "bases.json",
    "gems":    DATA_DIR / "gems.json",
    "skills":  DATA_DIR / "skills.json",
}

# Lua parsing regexes
RE_UNIQUES = re.compile(r'\[\[\n(.*?)\n\]\]', re.DOTALL)
RE_TABLE  = re.compile(r"\[\s*\"([^\"]+)\"\s*\]\s*=\s*\{([^}]+)\}", re.DOTALL)

headers = {"Accept": "application/vnd.github.v3+json"}


def fetch_dir(path):
    url = f"{REPO_API}/{path}?ref={BRANCH}"
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_file(download_url):
    resp = requests.get(download_url, timeout=10)
    resp.raise_for_status()
    return resp.text


def parse_uniques(content, file_path):
    items = []
    for block in RE_UNIQUES.findall(content):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines: continue
        name = lines[0]
        base = lines[1] if len(lines)>1 else ""
        mods, meta = [], {}
        for ln in lines[1:]:
            if ':' in ln and any(ln.startswith(k) for k in ("Variant:","Source:","League:")):
                k,v = ln.split(':',1); meta[k]=v.strip()
            elif not ln.startswith(('--','type:','tags:','subType:','socketLimit:','quality:')):
                mods.append(ln)
        items.append({"name": name, "baseType": base, "modifiers": mods, "metadata": meta})
    logger.info(f"Parsed {len(items)} uniques from {file_path}")
    return items


def parse_table(content, file_path):
    items = []
    for name, body in RE_TABLE.findall(content):
        meta = {}
        for ln in body.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith('--'): continue
            if '=' in ln:
                k,v = [x.strip().rstrip(',') for x in ln.split('=',1)]
                meta[k] = v
        items.append({"name": name, "baseType": name, "modifiers": [], "metadata": meta})
    logger.info(f"Parsed {len(items)} generic items from {file_path}")
    return items


def traverse_and_extract(base_path):
    results = defaultdict(list)
    def walk(path):
        try:
            entries = fetch_dir(path)
        except Exception as e:
            logger.error(f"Failed to list {path}: {e}")
            return
        for ent in entries:
            p = ent['path']
            if ent['type']=='dir':
                walk(p)
            elif p.endswith('.lua'):
                try:
                    txt = fetch_file(ent['download_url'])
                except Exception as e:
                    logger.error(f"Failed to fetch {p}: {e}")
                    continue
                if '/Uniques/' in p:
                    results['uniques'] += parse_uniques(txt, p)
                elif '/Bases/' in p:
                    results['bases']   += parse_table(txt, p)
                elif p.endswith('Gems.lua'):
                    results['gems']    += parse_table(txt, p)
                elif '/Skills/' in p:
                    results['skills']  += parse_table(txt, p)
                # ignore others
    walk('src/Data')
    return results


def save_json(data):
    for cat, items in data.items():
        path = CATEGORIES.get(cat)
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2)
            logger.info(f"Saved {len(items)} to {path.name}")


def main():
    logger.info("=== Starting POB data fetch ===")
    data = traverse_and_extract('src/Data')
    save_json(data)
    logger.info("=== Completed POB data fetch ===")
    print(f"Done: saved categories: {', '.join(data.keys())}")

if __name__ == '__main__':
    main()