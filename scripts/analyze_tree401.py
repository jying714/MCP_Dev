import json
import re
from collections import defaultdict
import os
import math
import logging
import uuid

# Set up logging with categories
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(category)s] - %(message)s')
logger = logging.getLogger(__name__)

def log_message(level, category, message):
    logger.log(level, message, extra={'category': category})

def analyze_tree401(json_file, output_file=r"C:\Users\jying\PycharmProjects\MCP_Dev\output\tree401_analysis.txt"):
    """
    Analyze tree401.json to extract detailed information about passive and ascendancy skill trees
    for accurate mapping of the Path of Exile 2 skill tree, excluding atlas data as irrelevant.
    Outputs findings to a text file in the specified output directory.
    Includes cleaning steps: remove self-loops, clamp outlier radii, mirror connections, and tag node types.
    """
    try:
        # Ensure output directory exists
        out_dir = os.path.dirname(output_file)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # Initialize error tracking
        errors = defaultdict(list)

        # Load JSON data
        log_message(logging.DEBUG, 'FILE', f"Loading {json_file}")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # === Preliminary Cleaning ===
        raw_passive_tree = data.get('passive_tree', {})
        raw_nodes = raw_passive_tree.get('nodes', {})
        self_loops = []
        outlier_count = 0
        # Remove self-loops and clamp radii
        for nid, node in raw_nodes.items():
            conns = node.get('connections', [])
            cleaned = []
            for c in conns:
                conn_id = str(c.get('id', c)) if isinstance(c, dict) else str(c)
                radius = c.get('radius', 0) if isinstance(c, dict) else 0
                if conn_id == str(nid):
                    self_loops.append(nid)
                    continue
                if radius == 2147483647:
                    radius = 0
                    outlier_count += 1
                cleaned.append({'id': conn_id, 'radius': radius})
            node['connections'] = cleaned
        # Mirror connections for undirected graph
        for nid, node in raw_nodes.items():
            for c in node.get('connections', []):
                cid = c['id']
                target = raw_nodes.get(cid)
                if target is not None:
                    if not any(str(x.get('id', x)) == str(nid) for x in target.get('connections', [])):
                        target.setdefault('connections', []).append({'id': str(nid), 'radius': c['radius']})

        # Tag each node with clear node_type
        passive_skills = data.get('passive_skills', {})
        for nid, node in raw_nodes.items():
            skill_id = node.get('skill_id', '')
            details = passive_skills.get(skill_id, {})
            node_type = 'Regular'
            if skill_id.startswith('Ascendancy'):
                node_type = 'Ascendancy'
            elif details.get('is_notable'):
                node_type = 'Notable'
            elif details.get('is_keystone'):
                node_type = 'Keystone'
            elif details.get('is_just_icon'):
                node_type = 'Mastery'
            elif details.get('is_multiple_choice'):
                node_type = 'Choice'
            elif 'socket' in skill_id.lower():
                node_type = 'Jewel Socket'
            elif 'Start' in skill_id:
                node_type = 'Start'
            elif 'Small' in skill_id:
                node_type = 'Small'
            node['node_type'] = node_type

        # Collect analysis lines
        analysis = []
        analysis.append("=== Data Cleaning Summary ===")
        analysis.append(f"Self-loops removed: {len(self_loops)}")
        analysis.append(f"Outlier radii clamped (2147483647→0): {outlier_count}")
        analysis.append("Connections mirrored to ensure undirected graph.")

        # Data structure overview
        analysis.append("=== Data Structure Overview ===")
        top_level_keys = list(data.keys())
        analysis.append(f"Top-level keys: {top_level_keys}")
        for key in top_level_keys:
            analysis.append(f"Key '{key}' type: {type(data[key]).__name__}")

        passive_tree = data.get('passive_tree', {})
        analysis.append("\npassive_tree structure:")
        analysis.append(f"- groups: dict, {len(passive_tree.get('groups', {}))} entries (fields: x, y, bg, proxy, unk2)")
        analysis.append(f"- nodes: dict, {len(passive_tree.get('nodes', {}))} entries (fields: skill_id, parent, radius, position, connections, node_type)")
        analysis.append(f"- root_passives: list, {len(passive_tree.get('root_passives', []))} entries")
        if passive_tree.get('groups'):
            sample_group_id = next(iter(passive_tree['groups']))
            analysis.append(f"Sample group ({sample_group_id}): {passive_tree['groups'][sample_group_id]}")
        if passive_tree.get('nodes'):
            sample_node_id = next(iter(passive_tree['nodes']))
            analysis.append(f"Sample node ({sample_node_id}): {passive_tree['nodes'][sample_node_id]}")

        # passive_skills overview
        analysis.append("\npassive_skills structure:")
        analysis.append(f"- dict, {len(passive_skills)} entries (fields: name, stats, is_notable, is_keystone, is_just_icon, is_multiple_choice, icon, ascendancy, etc.)")
        if passive_skills:
            sample_skill_id = next(iter(passive_skills))
            analysis.append(f"Sample skill ({sample_skill_id}): {passive_skills[sample_skill_id]}")

        # atlas tree minimal
        atlas_passive_tree = data.get('atlas_passive_tree', {})
        analysis.append("\natlas_passive_tree structure (excluded):")
        analysis.append(f"- groups: dict, {len(atlas_passive_tree.get('groups', {}))} entries")
        analysis.append(f"- nodes: dict, {len(atlas_passive_tree.get('nodes', {}))} entries")
        analysis.append(f"- root_passives: list, {len(atlas_passive_tree.get('root_passives', []))} entries")
        atlas_sub_trees = data.get('atlas_sub_trees', {})
        analysis.append("\natlas_sub_trees structure (excluded):")
        analysis.append(f"- dict, {len(atlas_sub_trees)} entries")

        # overlaps
        analysis.append("\nNode ID Overlaps")
        group_id_overlaps = set(passive_tree.get('groups', {})) & set(atlas_passive_tree.get('groups', {}))
        node_id_overlaps = set(passive_tree.get('nodes', {})) & set(atlas_passive_tree.get('nodes', {}))
        analysis.append(f"Group ID overlaps: {len(group_id_overlaps)}")
        analysis.append(f"Node ID overlaps: {len(node_id_overlaps)}")
        analysis.append(f"Nodes referencing overlapping group IDs: {len([n for n in passive_tree.get('nodes', {}).values() if str(n.get('parent','')) in group_id_overlaps])}")

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(analysis))
        log_message(logging.INFO, 'FILE', f"Analysis written to {output_file}")
    except Exception as e:
        log_message(logging.ERROR, 'GENERAL', f"Error analyzing {json_file}: {e}")
        raise

def main():
    json_file = '../data/tree401.json'
    if not os.path.exists(json_file):
        log_message(logging.ERROR, 'FILE', f"Error: {json_file} not found in current directory.")
        return
    analyze_tree401(json_file)

if __name__ == '__main__':
    main()
