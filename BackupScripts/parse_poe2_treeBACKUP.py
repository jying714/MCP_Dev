import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Set, Tuple, Any
from pathlib import Path

# Constants
INPUT_JSON = "tree401.json"
OUTPUT_DIR = "output"
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "skill_tree_data.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "skill_tree_extraction.log")
SCRIPT_VERSION = "1.0.0"

# Configure logging with rotation
def setup_logging():
    """Set up logging with rotation to prevent log file from growing indefinitely."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)  # 5MB per file, 3 backups
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

logger = setup_logging()

def load_json_file(filename: str) -> Dict[str, Any]:
    """Load JSON file with error handling."""
    try:
        if not os.path.exists(filename):
            logger.error(f"Input file {filename} not found")
            raise FileNotFoundError(f"{filename} not found")
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Successfully loaded {filename}")
        logger.debug(f"Top-level keys: {list(data.keys())}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in {filename}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
        raise

def infer_node_type(skill_id: str, skill_info: Dict[str, Any]) -> str:
    """Infer node type based on skill_id and skill_info."""
    if skill_info.get("is_keystone"):
        return "Keystone"
    if skill_info.get("is_notable"):
        return "Notable"
    if skill_info.get("is_just_icon"):
        return "Mastery"
    return "Small"

def extract_skill_tree_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant skill tree data for GUI rendering."""
    try:
        passive_tree = data.get("passive_tree", {})
        passive_skills = data.get("passive_skills", {})
        root_passives = set(str(rp) for rp in passive_tree.get("root_passives", []))
        groups = passive_tree.get("groups", {})
        nodes_raw = passive_tree.get("nodes", {})

        # Validate required data
        if not passive_tree or not passive_skills or not nodes_raw:
            logger.error("Missing required sections in JSON: passive_tree, passive_skills, or nodes")
            raise ValueError("Invalid JSON structure: missing required sections")

        # Class and Ascendancy metadata (hardcoded based on provided info)
        class_metadata = {
            "Marauder": {"attributes": ["Strength"], "starting_nodes": [], "ascendancies": []},
            "Warrior": {"attributes": ["Strength"], "starting_nodes": [], "ascendancies": ["Titan", "Warbringer", "Smith of Kitava"]},
            "Ranger": {"attributes": ["Dexterity"], "starting_nodes": [], "ascendancies": ["Deadeye", "Pathfinder"]},
            "Huntress": {"attributes": ["Dexterity"], "starting_nodes": [], "ascendancies": ["Ritualist", "Amazon"]},
            "Witch": {"attributes": ["Intelligence"], "starting_nodes": [], "ascendancies": ["Infernalist", "Blood Mage", "Lich"]},
            "Sorceress": {"attributes": ["Intelligence"], "starting_nodes": [], "ascendancies": ["Stormweaver", "Chronomancer"]},
            "Duelist": {"attributes": ["Strength", "Dexterity"], "starting_nodes": [], "ascendancies": []},
            "Mercenary": {"attributes": ["Strength", "Dexterity"], "starting_nodes": [], "ascendancies": ["Witchhunter", "Gemling Legionnaire", "Tactician"]},
            "Shadow": {"attributes": ["Dexterity", "Intelligence"], "starting_nodes": [], "ascendancies": []},
            "Monk": {"attributes": ["Dexterity", "Intelligence"], "starting_nodes": [], "ascendancies": ["Invoker", "Acolyte of Chayula"]},
            "Templar": {"attributes": ["Strength", "Intelligence"], "starting_nodes": [], "ascendancies": []},
            "Druid": {"attributes": ["Strength", "Intelligence"], "starting_nodes": [], "ascendancies": []},
        }

        # Data structures for output
        main_nodes: List[Dict[str, Any]] = []
        ascendancy_nodes: Dict[str, List[Dict[str, Any]]] = {class_name: [] for class_name in class_metadata.keys()}
        main_connections: List[Dict[str, int]] = []
        ascendancy_connections: Dict[str, List[Dict[str, int]]] = {class_name: [] for class_name in class_metadata.keys()}
        node_ids: Set[int] = set()
        skill_data_keys = set(passive_skills.keys())

        # Filtering for invalid nodes
        invalid_prefixes = ["jewel_slot", "placeholder", "start", "class", "atlas"]

        # Process nodes in a single pass
        for node_id, node in nodes_raw.items():
            try:
                node_id_int = int(node_id)
            except ValueError:
                logger.warning(f"Skipping invalid node ID: {node_id}")
                continue

            raw_skill_id = node.get("skill_id", "").strip()
            is_jewel_socket = node.get("is_jewel_socket", False)
            is_class_start = node.get("is_class_start", False)
            is_multiple_choice = node.get("is_multiple_choice", False)
            is_proxy = node.get("is_proxy", False)

            # Filter invalid nodes
            if not raw_skill_id:
                logger.debug(f"Filtering node {node_id}: Empty skill_id")
                continue
            if any(raw_skill_id.lower().startswith(prefix.lower()) for prefix in invalid_prefixes):
                logger.debug(f"Filtering node {node_id}: Invalid skill_id prefix: {raw_skill_id}")
                continue
            if is_jewel_socket or is_class_start or is_multiple_choice or is_proxy:
                logger.debug(f"Filtering node {node_id}: Jewel socket, class start, multiple choice, or proxy")
                continue
            if raw_skill_id not in skill_data_keys:
                logger.debug(f"Filtering node {node_id}: Skill_id not in passive_skills: {raw_skill_id}")
                continue

            skill_info = passive_skills.get(raw_skill_id, {})
            if not skill_info:
                logger.debug(f"Filtering node {node_id}: No skill data for skill_id: {raw_skill_id}")
                continue

            # Determine if this is an Ascendancy node
            is_ascendancy = raw_skill_id.lower().startswith("ascendancy")
            node_type = infer_node_type(raw_skill_id, skill_info)
            group_id = str(node.get("parent", ""))
            group = groups.get(group_id, {})
            x = float(group.get("x", 0))
            y = float(group.get("y", 0))

            # Node data
            node_data = {
                "id": node_id_int,
                "skill_id": raw_skill_id,
                "name": skill_info.get("name", raw_skill_id),
                "effects": skill_info.get("stats", {}),
                "type": node_type,
                "group_id": group_id if group_id else None,
                "x": x,
                "y": y,
                "is_root": str(node_id) in root_passives
            }

            # Assign node to main tree or Ascendancy tree
            if is_ascendancy:
                # Extract class from skill_id (e.g., "AscendancyWarrior1" -> "Warrior")
                class_match = next((cls for cls in class_metadata.keys() if cls.lower() in raw_skill_id.lower()), None)
                if class_match:
                    ascendancy_nodes[class_match].append(node_data)
                else:
                    logger.warning(f"Could not determine class for Ascendancy node {node_id}: {raw_skill_id}")
                    continue
            else:
                main_nodes.append(node_data)
                if node_data["is_root"]:
                    for class_name, metadata in class_metadata.items():
                        if any(attr in metadata["attributes"] for attr in ["Strength"]):  # Simplified class detection
                            if "Strength" in metadata["attributes"] and class_name in ["Warrior", "Marauder"]:
                                metadata["starting_nodes"].append(node_id_int)
                            elif "Dexterity" in metadata["attributes"] and class_name in ["Ranger", "Huntress"]:
                                metadata["starting_nodes"].append(node_id_int)
                            elif "Intelligence" in metadata["attributes"] and class_name in ["Witch", "Sorceress"]:
                                metadata["starting_nodes"].append(node_id_int)
                            elif sorted(metadata["attributes"]) == ["Dexterity", "Intelligence"] and class_name in ["Shadow", "Monk"]:
                                metadata["starting_nodes"].append(node_id_int)
                            elif sorted(metadata["attributes"]) == ["Strength", "Dexterity"] and class_name in ["Duelist", "Mercenary"]:
                                metadata["starting_nodes"].append(node_id_int)
                            elif sorted(metadata["attributes"]) == ["Intelligence", "Strength"] and class_name in ["Templar", "Druid"]:
                                metadata["starting_nodes"].append(node_id_int)

            node_ids.add(node_id_int)

        # Process connections
        for node in main_nodes:
            node_id = node["id"]
            node_data = nodes_raw.get(str(node_id), {})
            for conn in node_data.get("connections", []):
                target_id = conn.get("id")
                if not target_id:
                    logger.warning(f"Skipping connection with missing ID from node {node_id}")
                    continue
                try:
                    target_id = int(target_id)
                except ValueError:
                    logger.warning(f"Skipping invalid connection ID {target_id} from node {node_id}")
                    continue
                if target_id not in node_ids:
                    logger.debug(f"Invalid connection to node ID {target_id} from node {node_id}")
                    continue
                # Ensure target node is in main tree
                if any(n["id"] == target_id for n in main_nodes):
                    main_connections.append({"from": node_id, "to": target_id})

        # Process Ascendancy connections
        for class_name, nodes in ascendancy_nodes.items():
            ascendancy_node_ids = {n["id"] for n in nodes}
            for node in nodes:
                node_id = node["id"]
                node_data = nodes_raw.get(str(node_id), {})
                for conn in node_data.get("connections", []):
                    target_id = conn.get("id")
                    if not target_id:
                        logger.warning(f"Skipping Ascendancy connection with missing ID from node {node_id}")
                        continue
                    try:
                        target_id = int(target_id)
                    except ValueError:
                        logger.warning(f"Skipping invalid Ascendancy connection ID {target_id} from node {node_id}")
                        continue
                    if target_id not in ascendancy_node_ids:
                        logger.debug(f"Invalid Ascendancy connection to node ID {target_id} from node {node_id}")
                        continue
                    ascendancy_connections[class_name].append({"from": node_id, "to": target_id})

        # Compile output
        output_data = {
            "main_tree": {
                "nodes": main_nodes,
                "connections": main_connections,
                "groups": groups
            },
            "ascendancy_trees": {
                class_name: {
                    "nodes": nodes,
                    "connections": ascendancy_connections[class_name]
                }
                for class_name, nodes in ascendancy_nodes.items() if nodes
            },
            "classes": class_metadata,
            "metadata": {
                "script_version": SCRIPT_VERSION,
                "total_main_nodes": len(main_nodes),
                "total_ascendancy_nodes": {class_name: len(nodes) for class_name, nodes in ascendancy_nodes.items() if nodes}
            }
        }

        logger.info(f"Extracted {len(main_nodes)} main tree nodes and {len(main_connections)} connections")
        logger.info(f"Ascendancy nodes extracted: { {k: len(v) for k, v in ascendancy_nodes.items() if v} }")
        return output_data

    except Exception as e:
        logger.error(f"Error extracting skill tree data: {e}")
        raise

def save_json_file(data: Dict[str, Any], filename: str):
    """Save data to JSON file with error handling."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved extracted data to {filename}")
    except Exception as e:
        logger.error(f"Failed to save JSON to {filename}: {e}")
        raise

def main():
    """Main function to extract skill tree data from tree401.json."""
    try:
        logger.info(f"Starting script version {SCRIPT_VERSION}")

        # Load data
        data = load_json_file(INPUT_JSON)

        # Extract relevant data
        extracted_data = extract_skill_tree_data(data)

        # Save output
        save_json_file(extracted_data, OUTPUT_JSON)

        logger.info("Script completed successfully")
    except Exception as e:
        logger.error(f"Script failed: {e}")
        raise

if __name__ == "__main__":
    main()