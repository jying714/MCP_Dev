# scripts/analyze_tree401.py
#!/usr/bin/env python3
import json
import logging
from collections import defaultdict
from pathlib import Path

# === Path setup ===
HERE         = Path(__file__).parent
PROJECT_ROOT = HERE.parent
DATA_DIR     = PROJECT_ROOT / "data"
OUTPUT_DIR   = PROJECT_ROOT / "output"
LOG_DIR      = PROJECT_ROOT / "logs" / "analyze_tree401"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# === Logging Setup ===
LOG_FILE = LOG_DIR / "analyze_tree401.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(category)s] - %(message)s"
)
logger = logging.getLogger(__name__)

def log_message(level, category, message):
    logger.log(level, message, extra={"category": category})

def analyze_tree401(json_file: Path,
                    output_file: Path = OUTPUT_DIR / "tree401_analysis.txt"):
    """
    Analyze tree401.json to extract detailed information about passive and ascendancy skill trees
    for accurate mapping of the Path of Exile 2 skill tree.
    Outputs findings to a text file in output/.
    """
    try:
        # Load JSON data
        log_message(logging.DEBUG, "FILE", f"Loading {json_file}")
        with json_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Preliminary Cleaning
        raw_passive = data.get("passive_tree", {}).get("nodes", {})
        self_loops = []
        outlier_count = 0

        # Remove self-loops & clamp huge radii; mirror connections
        for nid, node in raw_passive.items():
            conns = node.get("connections", [])
            cleaned = []
            for c in conns:
                cid = str(c.get("id", c)) if isinstance(c, dict) else str(c)
                radius = c.get("radius", 0) if isinstance(c, dict) else 0
                if cid == str(nid):
                    self_loops.append(nid)
                    continue
                if radius == 2147483647:
                    radius = 0
                    outlier_count += 1
                cleaned.append({"id": cid, "radius": radius})
            node["connections"] = cleaned

        # Mirror undirected edges
        for nid, node in raw_passive.items():
            for c in node["connections"]:
                cid = c["id"]
                target = raw_passive.get(cid)
                if target is not None:
                    if not any(str(x.get("id", x)) == str(nid) for x in target.get("connections", [])):
                        target.setdefault("connections", []).append({"id": str(nid), "radius": c["radius"]})

        # Tag node types
        passive_skills = data.get("passive_skills", {})
        for nid, node in raw_passive.items():
            sid = node.get("skill_id", "")
            details = passive_skills.get(sid, {})
            if sid.startswith("Ascendancy"):
                t = "Ascendancy"
            elif details.get("is_keystone"):
                t = "Keystone"
            elif details.get("is_notable"):
                t = "Notable"
            elif details.get("is_just_icon"):
                t = "Mastery"
            elif details.get("is_multiple_choice"):
                t = "Choice"
            elif "socket" in sid.lower():
                t = "Jewel Socket"
            elif "Start" in sid:
                t = "Start"
            elif "Small" in sid:
                t = "Small"
            else:
                t = "Regular"
            node["node_type"] = t

        # Build analysis report
        analysis = [
            "=== Data Cleaning Summary ===",
            f"Self-loops removed: {len(self_loops)}",
            f"Outlier radii clamped: {outlier_count}",
            "Connections mirrored for undirected graph.",
            "",
            "=== Data Structure Overview ===",
            f"Top-level keys: {list(data.keys())}"
        ]

        pt = data.get("passive_tree", {})
        analysis += [
            f"\npassive_tree overview:",
            f"- groups: {len(pt.get('groups', {}))}",
            f"- nodes: {len(pt.get('nodes', {}))}",
            f"- root_passives: {len(pt.get('root_passives', []))}"
        ]

        if pt.get("nodes"):
            sample = next(iter(pt["nodes"]))
            analysis.append(f" Sample node ({sample}): {pt['nodes'][sample]}")

        # Write to output
        with output_file.open("w", encoding="utf-8") as f:
            f.write("\n".join(analysis))

        log_message(logging.INFO, "FILE", f"Analysis written to {output_file}")

    except Exception as e:
        log_message(logging.ERROR, "GENERAL", f"Error analyzing {json_file}: {e}")
        raise

def main():
    json_path = DATA_DIR / "tree401.json"
    if not json_path.exists():
        log_message(logging.ERROR, "FILE", f"Input not found: {json_path}")
        return
    analyze_tree401(json_path)

if __name__ == "__main__":
    main()
