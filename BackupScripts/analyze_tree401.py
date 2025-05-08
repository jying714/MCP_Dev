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

def analyze_tree401(json_file, output_file="tree401_analysis.txt"):
    """
    Analyze tree401.json to extract detailed information about passive and ascendancy skill trees
    for accurate mapping of the Path of Exile 2 skill tree, excluding atlas data as irrelevant.
    Outputs findings to a text file, maintaining full scope analysis for future use with AI or other tools.
    Includes clarification requests for unresolved issues.
    """
    try:
        # Initialize error tracking
        errors = defaultdict(list)

        # Load JSON data
        log_message(logging.DEBUG, 'FILE', f"Loading {json_file}")
        with open(json_file, 'r') as f:
            data = json.load(f)

        # Initialize output
        analysis = []

        # 1. Data Structure Overview
        analysis.append("=== Data Structure Overview ===")
        top_level_keys = list(data.keys())
        analysis.append(f"Top-level keys: {top_level_keys}")
        for key in top_level_keys:
            analysis.append(f"Key '{key}' type: {type(data[key]).__name__}")
        # Passive Tree Structure
        passive_tree = data.get('passive_tree', {})
        analysis.append("\npassive_tree structure:")
        analysis.append(f"- groups: dict, {len(passive_tree.get('groups', {}))} entries (fields: x, y, bg, proxy, unk2)")
        analysis.append(f"- nodes: dict, {len(passive_tree.get('nodes', {}))} entries (fields: skill_id, parent, radius, position, connections)")
        analysis.append(f"- root_passives: list, {len(passive_tree.get('root_passives', []))} entries")
        if passive_tree.get('groups'):
            sample_group_id = next(iter(passive_tree['groups']))
            analysis.append(f"Sample group ({sample_group_id}): {passive_tree['groups'][sample_group_id]}")
        if passive_tree.get('nodes'):
            sample_node_id = next(iter(passive_tree['nodes']))
            sample_node = passive_tree['nodes'][sample_node_id]
            analysis.append(f"Sample node ({sample_node_id}): {sample_node}")
        # Passive Skills Structure
        passive_skills = data.get('passive_skills', {})
        analysis.append("\npassive_skills structure:")
        analysis.append(f"- dict, {len(passive_skills)} entries (fields: name, stats, is_notable, is_keystone, is_just_icon, is_multiple_choice, icon, ascendancy, etc.)")
        if passive_skills:
            sample_skill_id = next(iter(passive_skills))
            analysis.append(f"Sample skill ({sample_skill_id}): {passive_skills[sample_skill_id]}")
        # Atlas Passive Tree Structure (Minimal)
        atlas_passive_tree = data.get('atlas_passive_tree', {})
        analysis.append("\natlas_passive_tree structure (excluded from analysis as irrelevant):")
        analysis.append(f"- groups: dict, {len(atlas_passive_tree.get('groups', {}))} entries")
        analysis.append(f"- nodes: dict, {len(atlas_passive_tree.get('nodes', {}))} entries")
        analysis.append(f"- root_passives: list, {len(atlas_passive_tree.get('root_passives', []))} entries")
        # Atlas Sub-Trees Structure (Minimal)
        atlas_sub_trees = data.get('atlas_sub_trees', {})
        analysis.append("\natlas_sub_trees structure (excluded from analysis as irrelevant):")
        analysis.append(f"- dict, {len(atlas_sub_trees)} entries")

        # Check for Node ID Overlaps
        analysis.append("\nNode ID Overlaps")
        passive_group_ids = set(passive_tree.get('groups', {}).keys())
        passive_node_ids = set(passive_tree.get('nodes', {}).keys())
        atlas_group_ids = set(atlas_passive_tree.get('groups', {}).keys())
        atlas_node_ids = set(atlas_passive_tree.get('nodes', {}).keys())
        group_id_overlaps = passive_group_ids.intersection(atlas_group_ids)
        node_id_overlaps = passive_node_ids.intersection(atlas_node_ids)
        analysis.append(f"Group ID overlaps between passive_tree and atlas_passive_tree: {len(group_id_overlaps)}")
        if group_id_overlaps:
            analysis.append("Sample group ID overlaps with data:")
            sample_overlaps = sorted(list(group_id_overlaps))[:5]
            for gid in sample_overlaps:
                passive_group = passive_tree['groups'].get(gid, {})
                atlas_group = atlas_passive_tree['groups'].get(gid, {})
                analysis.append(f"- Group ID {gid}: passive_tree.groups: {passive_group}, atlas_passive_tree.groups: {atlas_group}")
        analysis.append(f"Node ID overlaps between passive_tree and atlas_passive_tree: {len(node_id_overlaps)}")
        if node_id_overlaps:
            analysis.append(f"Sample node ID overlaps: {sorted(list(node_id_overlaps))[:5]}")
            for nid in sorted(list(node_id_overlaps))[:5]:
                errors['NodeIDOverlap'].append(f"Node ID {nid} appears in both passive_tree.nodes and atlas_passive_tree.nodes")
        # Check for ambiguity in references
        ambiguous_references = []
        for node_id, node in passive_tree.get('nodes', {}).items():
            parent = str(node.get('parent', ''))
            if parent in group_id_overlaps:
                ambiguous_references.append(f"Node {node_id} (skill_id: {node.get('skill_id', 'N/A')}) references overlapping group {parent}")
        analysis.append(f"Nodes referencing overlapping group IDs: {len(ambiguous_references)}")
        if ambiguous_references:
            analysis.append("Sample nodes with ambiguous group references:")
            for ref in ambiguous_references[:5]:
                analysis.append(f"- {ref}")
        analysis.append("Note: Overlaps are likely intentional due to separate namespaces for passive_tree and atlas_passive_tree, but ambiguous references may cause issues.")

        # 2. Passive Tree Analysis
        analysis.append("\n=== Passive Tree Analysis ===")
        groups = passive_tree.get('groups', {})
        nodes = passive_tree.get('nodes', {})
        root_passives = passive_tree.get('root_passives', [])

        # Log basic stats
        analysis.append(f"Total groups: {len(groups)}")
        analysis.append(f"Total nodes: {len(nodes)}")
        analysis.append(f"Root passives: {len(root_passives)} (IDs: {root_passives})")

        # Node Validation
        analysis.append("\nNode Validation")
        node_dict = {}
        invalid_nodes = 0
        missing_skill_ids = 0
        missing_parents = 0
        for node_id, node in nodes.items():
            node_id = str(node_id)
            if not isinstance(node, dict):
                log_message(logging.WARNING, 'NODE_ERROR', f"Node {node_id} is not a dict: {node}")
                errors['InvalidNode'].append(f"Node {node_id}: {node}")
                invalid_nodes += 1
                continue
            if 'skill_id' not in node:
                log_message(logging.WARNING, 'NODE_ERROR', f"Node {node_id} missing skill_id: {node}")
                errors['MissingSkillID'].append(f"Node {node_id}: {node}")
                missing_skill_ids += 1
            if 'parent' not in node:
                log_message(logging.WARNING, 'NODE_ERROR', f"Node {node_id} missing parent: {node}")
                errors['MissingParent'].append(f"Node {node_id}: {node}")
                missing_parents += 1
            node_dict[node_id] = node
        analysis.append(f"Invalid nodes: {invalid_nodes}")
        analysis.append(f"Nodes missing skill_id: {missing_skill_ids}")
        analysis.append(f"Nodes missing parent: {missing_parents}")

        # Connections Format Analysis
        analysis.append("\nConnections Format Analysis")
        connection_formats = defaultdict(int)
        for node_id, node in node_dict.items():
            connections = node.get('connections', [])
            if not connections:
                connection_formats['Empty'] += 1
                continue
            first_conn = connections[0]
            if isinstance(first_conn, dict):
                if 'id' in first_conn:
                    connection_formats['List of Dicts with ID'] += 1
                else:
                    connection_formats['List of Dicts without ID'] += 1
                    errors['InvalidConnectionFormat'].append(f"Node {node_id}: Connections dict missing 'id': {connections[:3]}")
            elif isinstance(first_conn, (str, int)):
                connection_formats['List of IDs'] += 1
            else:
                connection_formats['Unknown'] += 1
                errors['InvalidConnectionFormat'].append(f"Node {node_id}: Unknown connections format: {connections[:3]}")
        analysis.append("Connections format distribution:")
        for fmt, count in connection_formats.items():
            analysis.append(f"- {fmt}: {count} nodes")

        # Connection Radius Analysis
        analysis.append("\nConnection Radius Analysis")
        connection_radius_counts = defaultdict(int)
        outlier_radius_nodes = []
        normal_radius_samples = []
        radius_by_node_type = defaultdict(lambda: defaultdict(int))
        radius_by_sub_variant = defaultdict(lambda: defaultdict(int))
        for node_id, node in node_dict.items():
            skill_id = node.get('skill_id', '')
            is_ascendancy = skill_id.startswith('Ascendancy')
            sub_variant = 'Passive'
            if is_ascendancy:
                match = re.match(r'Ascendancy(\w+?)(\d+)?(?:\w+)?', skill_id)
                if match:
                    sub_variant = f"{match.group(1)}{match.group(2) or ''}"
            node_type = 'Regular'
            if passive_skills.get(skill_id, {}).get('is_notable'):
                node_type = 'Notable'
            elif passive_skills.get(skill_id, {}).get('is_keystone'):
                node_type = 'Keystone'
            elif passive_skills.get(skill_id, {}).get('is_just_icon'):
                node_type = 'Mastery'
            elif 'Start' in skill_id:
                node_type = 'Start'
            elif 'Small' in skill_id:
                node_type = 'Small'
            elif 'socket' in skill_id.lower():
                node_type = 'Jewel Socket'
            connections = node.get('connections', [])
            for conn in connections:
                if isinstance(conn, dict):
                    radius = conn.get('radius', 0)
                    connection_radius_counts[radius] += 1
                    radius_by_node_type[node_type][radius] += 1
                    radius_by_sub_variant[sub_variant][radius] += 1
                    if radius == 2147483647:
                        conn_id = str(conn.get('id', 'Unknown'))
                        conn_skill_id = node_dict.get(conn_id, {}).get('skill_id', 'N/A')
                        outlier_radius_nodes.append((node_id, skill_id, conn_id, conn_skill_id))
                        errors['OutlierConnectionRadius'].append(f"Node {node_id} ({skill_id}) -> Node {conn_id} ({conn_skill_id})")
                    elif radius in [-9, 0, 7] and len(normal_radius_samples) < 5:
                        conn_id = str(conn.get('id', 'Unknown'))
                        conn_skill_id = node_dict.get(conn_id, {}).get('skill_id', 'N/A')
                        normal_radius_samples.append((node_id, skill_id, conn_id, conn_skill_id, radius))
        analysis.append(f"Unique connection radius values: {sorted(connection_radius_counts.keys())}")
        analysis.append(f"Connection radius distribution: {dict(connection_radius_counts)}")
        analysis.append(f"Nodes with outlier radius (2147483647): {len(outlier_radius_nodes)}")
        if outlier_radius_nodes:
            analysis.append("Sample nodes with outlier radius:")
            for node_id, skill_id, conn_id, conn_skill_id in outlier_radius_nodes[:10]:
                analysis.append(f"- Node {node_id} ({skill_id}) -> Node {conn_id} ({conn_skill_id})")
        analysis.append("Sample connections with normal radius values (e.g., -9, 0, 7):")
        for node_id, skill_id, conn_id, conn_skill_id, radius in normal_radius_samples:
            analysis.append(f"- Node {node_id} ({skill_id}) -> Node {conn_id} ({conn_skill_id}), radius: {radius}")
        analysis.append("Connection radius by node type:")
        for node_type, radius_counts in radius_by_node_type.items():
            analysis.append(f"- {node_type}: {dict(radius_counts)}")
        analysis.append("Connection radius by sub-variant:")
        for sub_variant, radius_counts in radius_by_sub_variant.items():
            analysis.append(f"- {sub_variant}: {dict(radius_counts)}")
        analysis.append("Note: The 'radius' field likely affects visual path styling or positioning adjustments (e.g., for ascendancy nodes in the circular layout). The value 2147483647 is treated as a data error (placeholder for missing values).")

        # Node-to-Group Mapping
        analysis.append("\nNode-to-Group Mapping")
        node_ids = set(node_dict.keys())
        group_ids = set(groups.keys())
        node_group_matches = node_ids.intersection(group_ids)
        analysis.append(f"Node IDs matching group IDs: {len(node_group_matches)}")
        if node_group_matches:
            analysis.append("Sample node-group matches:")
            for nid in sorted(list(node_group_matches))[:5]:
                node = node_dict.get(nid, {})
                skill_id = node.get('skill_id', 'N/A')
                parent = node.get('parent', 'N/A')
                connections = node.get('connections', [])
                skill_details = passive_skills.get(skill_id, {})
                node_type = 'Regular'
                if skill_details.get('is_notable'):
                    node_type = 'Notable'
                elif skill_details.get('is_keystone'):
                    node_type = 'Keystone'
                elif skill_details.get('is_just_icon'):
                    node_type = 'Mastery'
                elif skill_details.get('is_multiple_choice'):
                    node_type = 'Choice'
                elif 'Start' in skill_id:
                    node_type = 'Start'
                elif 'Small' in skill_id:
                    node_type = 'Small'
                elif 'socket' in skill_id.lower():
                    node_type = 'Jewel Socket'
                is_root = any(str(conn.get('id', conn)) == nid for n in nodes.values() for conn in n.get('connections', []))
                is_leaf = len(connections) == 0
                analysis.append(f"Node/Group {nid}: skill_id={skill_id}, parent={parent}, connections={len(connections)}, type={node_type}, root={is_root}, leaf={is_leaf}")

        # Parent Analysis
        analysis.append("\nParent Analysis")
        parent_to_nodes = defaultdict(list)
        nodes_with_parent = 0
        for node_id, node in node_dict.items():
            parent = node.get('parent')
            if parent is not None:
                nodes_with_parent += 1
                parent_to_nodes[str(parent)].append(node_id)
            else:
                errors['MissingParent'].append(f"Node {node_id}: No parent")
        analysis.append(f"Nodes with parent: {nodes_with_parent}")
        parent_ids = set(parent_to_nodes.keys())
        parent_in_nodes = parent_ids.intersection(node_ids)
        parent_in_groups = parent_ids.intersection(group_ids)
        analysis.append(f"Parent IDs matching node IDs: {len(parent_in_nodes)}")
        analysis.append(f"Parent IDs matching group IDs: {len(parent_in_groups)}")
        unmapped_parents = parent_ids - group_ids
        analysis.append(f"Nodes with unmapped parents: {len(unmapped_parents)}")
        if unmapped_parents:
            analysis.append(f"Sample unmapped parents: {sorted(list(unmapped_parents))[:5]}")

        # Group Node Counts
        analysis.append("\nGroup Node Counts")
        group_node_counts = defaultdict(int)
        for parent, node_ids in parent_to_nodes.items():
            if parent in group_ids:
                group_node_counts[parent] += len(node_ids)
        analysis.append(f"Groups with nodes: {len(group_node_counts)}")
        if group_node_counts:
            analysis.append("Sample group node counts:")
            for group_id, count in sorted(group_node_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                sample_nodes = parent_to_nodes[group_id][:5]
                node_types = [passive_skills.get(node_dict[nid].get('skill_id', ''), {}).get('is_notable', False) and 'Notable' or
                              passive_skills.get(node_dict[nid].get('skill_id', ''), {}).get('is_keystone', False) and 'Keystone' or
                              'Start' in node_dict[nid].get('skill_id', '') and 'Start' or
                              'Small' in node_dict[nid].get('skill_id', '') and 'Small' or
                              'socket' in node_dict[nid].get('skill_id', '').lower() and 'Jewel Socket' or 'Regular' for nid in sample_nodes]
                analysis.append(f"Group {group_id}: {count} nodes (e.g., {sample_nodes}, types: {node_types})")

        # Position and Radius Analysis
        analysis.append("\nPosition and Radius Analysis")
        position_counts = defaultdict(int)
        radius_counts = defaultdict(int)
        position_samples = []
        coordinate_ranges = {'x': [], 'y': []}
        node_positions = {}
        overlapping_nodes = defaultdict(list)
        for node_id, node in node_dict.items():
            position = node.get('position', 0)
            radius = node.get('radius', 0)
            position_counts[position] += 1
            radius_counts[radius] += 1
            group = groups.get(str(node.get('parent', '')), {})
            group_x = group.get('x', 0)
            group_y = group.get('y', 0)
            coordinate_ranges['x'].append(group_x)
            coordinate_ranges['y'].append(group_y)
            if position > 0:
                angle = (position / 140) * 2 * math.pi
                offset_x = radius * 10 * math.cos(angle)
                offset_y = radius * 10 * math.sin(angle)
                final_x = group_x + offset_x
                final_y = group_y + offset_y
                skill_id = node.get('skill_id', 'N/A')
                position_samples.append((node_id, skill_id, position, radius, group_x, group_y, final_x, final_y))
                node_positions[node_id] = (final_x, final_y)
                overlapping_nodes[(group.get('parent', 'N/A'), round(final_x, 2), round(final_y, 2))].append(node_id)
        analysis.append(f"Nodes with position: {sum(position_counts.values())}")
        analysis.append(f"Nodes with non-zero position: {sum(v for k, v in position_counts.items() if k > 0)}")
        analysis.append(f"Unique position values: {sorted(position_counts.keys())[:10]}...")
        analysis.append(f"Position distribution: {dict(position_counts)}")
        analysis.append(f"Nodes with radius: {sum(radius_counts.values())}")
        analysis.append(f"Unique radius values: {sorted(radius_counts.keys())}")
        analysis.append(f"Radius distribution: {dict(radius_counts)}")
        analysis.append(f"Coordinate ranges: x=[{min(coordinate_ranges['x']):.2f}, {max(coordinate_ranges['x']):.2f}], y=[{min(coordinate_ranges['y']):.2f}, {max(coordinate_ranges['y']):.2f}]")
        overlaps = [(k, v) for k, v in overlapping_nodes.items() if len(v) > 1]
        analysis.append(f"Overlapping nodes: {len(overlaps)}")
        if overlaps:
            analysis.append("Sample overlapping nodes:")
            for (parent, x, y), node_ids in overlaps[:5]:
                analysis.append(f"Group {parent}, ({x:.2f}, {y:.2f}): {node_ids}")
        if position_samples:
            analysis.append("Sample position mappings (non-zero position):")
            for nid, skill_id, pos, rad, gx, gy, fx, fy in position_samples[:5]:
                analysis.append(f"Node {nid} ({skill_id}): position={pos}, radius={rad}, group_x={gx}, group_y={gy}, final_x={fx:.2f}, final_y={fy:.2f}")

        # Group Fields Analysis
        analysis.append("\nGroup Fields Analysis")
        group_fields = set()
        for group in groups.values():
            group_fields.update(group.keys())
        analysis.append(f"Group fields: {sorted(group_fields)}")
        bg_values = set(group.get('bg') for group in groups.values())
        proxy_values = set(group.get('proxy') for group in groups.values())
        unk2_counts = defaultdict(int)
        unk2_sub_variants = defaultdict(set)
        for group_id, group in groups.items():
            unk2 = group.get('unk2')
            unk2_counts[unk2] += 1
            for nid in parent_to_nodes[group_id]:
                skill_id = node_dict[nid].get('skill_id', '')
                if skill_id.startswith('Ascendancy'):
                    match = re.match(r'Ascendancy(\w+?)(\d+)?(?:\w+)?', skill_id)
                    if match:
                        sub_variant = f"{match.group(1)}{match.group(2) or ''}"
                        unk2_sub_variants[unk2].add(sub_variant)
        analysis.append(f"Unique bg values: {sorted(bg_values)}")
        analysis.append(f"Unique proxy values: {sorted(proxy_values)}")
        analysis.append("unk2 value distribution:")
        for unk2, count in sorted(unk2_counts.items()):
            sub_variants = sorted(unk2_sub_variants[unk2]) or ['None']
            analysis.append(f"- unk2={unk2}: {count} groups, sub-variants: {sub_variants}")

        # Starting Nodes Analysis
        analysis.append("\n=== Starting Nodes Analysis ===")
        # Define starting nodes and their expected options with corrected stats
        starting_nodes = {
            'Warrior': {
                'location': 'Bottom left (South west)',
                'options': [
                    {'name': 'Melee damage', 'stats': {'melee_damage_+%': 10}},
                    {'name': 'Armour', 'stats': {'base_physical_damage_reduction_rating': 20}}
                ],
                'x_range': (-22256.96, -5000),  # Expected negative x for left side
                'y_range': (-5000, 18720.7)    # Expected positive y for bottom
            },
            'Witch': {
                'location': 'Top (North)',
                'options': [
                    {'name': 'Spell and minion damage', 'stats': {'spell_damage_+%': 8, 'minion_damage_+%': 8}},
                    {'name': 'Energy Shield', 'stats': {'base_maximum_energy_shield': 10}}
                ],
                'x_range': (-5000, 5000),      # Expected central x for top
                'y_range': (-18720.7, -5000)   # Expected negative y for top
            },
            'Ranger': {
                'location': 'Bottom right (South east)',
                'options': [
                    {'name': 'Projectile damage', 'stats': {'projectile_damage_+%': 10}},
                    {'name': 'Evasion', 'stats': {'base_evasion_rating': 16}}
                ],
                'x_range': (5000, 21814.27),   # Expected positive x for right side
                'y_range': (-5000, 18720.7)    # Expected positive y for bottom
            },
            'Sorceress': {
                'location': 'Top (North)',
                'options': [
                    {'name': 'Spell and minion damage', 'stats': {'spell_damage_+%': 8, 'minion_damage_+%': 8}},
                    {'name': 'Energy Shield', 'stats': {'base_maximum_energy_shield': 10}}
                ],
                'x_range': (-5000, 5000),      # Expected central x for top
                'y_range': (-18720.7, -5000)   # Expected negative y for top
            },
            'Huntress': {
                'location': 'Bottom right (South east)',
                'options': [
                    {'name': 'Projectile damage', 'stats': {'projectile_damage_+%': 10}},
                    {'name': 'Evasion', 'stats': {'base_evasion_rating': 16}}
                ],
                'x_range': (5000, 21814.27),   # Expected positive x for right side
                'y_range': (-5000, 18720.7)    # Expected positive y for bottom
            },
            'Mercenary': {
                'location': 'Bottom (South)',
                'options': [
                    {'name': 'Projectile damage', 'stats': {'projectile_damage_+%': 10}},
                    {'name': 'Armour and evasion', 'stats': {'base_physical_damage_reduction_rating': 10, 'base_evasion_rating': 8}}
                ],
                'x_range': (-5000, 5000),      # Expected central x for bottom
                'y_range': (-5000, 18720.7)    # Expected positive y for bottom
            },
            'Monk': {
                'location': 'Top right (North east)',
                'options': [
                    {'name': 'Skill speed', 'stats': {'cast_speed_+%': 3}},
                    {'name': 'Evasion and energy shield', 'stats': {'base_evasion_rating': 8, 'base_maximum_energy_shield': 5}}
                ],
                'x_range': (5000, 21814.27),   # Expected positive x for right side
                'y_range': (-18720.7, -5000)   # Expected negative y for top
            }
        }
        # Identify starting nodes from root_passives
        root_passive_nodes = []
        for root_id in root_passives:
            root_id_str = str(root_id)
            if root_id_str in node_dict:
                root_node = node_dict[root_id_str]
                root_passive_nodes.append((root_id_str, root_node))
            else:
                errors['MissingRootPassive'].append(f"Root passive {root_id} not found in nodes")
        analysis.append(f"Root passives found: {len(root_passive_nodes)}")
        # Map root passives to classes
        class_to_start_nodes = {}
        stat_mismatches = []
        for class_name, class_info in starting_nodes.items():
            class_start_nodes = []
            expected_options = class_info['options']
            x_range = class_info['x_range']
            y_range = class_info['y_range']
            for root_id, root_node in root_passive_nodes:
                connections = root_node.get('connections', [])
                parent = str(root_node.get('parent', 'N/A'))
                group = groups.get(parent, {})
                group_x = group.get('x', 0)
                group_y = group.get('y', 0)
                position_valid = (x_range[0] <= group_x <= x_range[1]) and (y_range[0] <= group_y <= y_range[1])
                if not position_valid:
                    continue
                # Get connected nodes
                connected_nodes = []
                for conn in connections:
                    conn_id = str(conn.get('id', ''))
                    if conn_id in node_dict:
                        conn_node = node_dict[conn_id]
                        skill_id = conn_node.get('skill_id', '')
                        skill_details = passive_skills.get(skill_id, {})
                        stats = skill_details.get('stats', {})
                        name = skill_details.get('name', 'Unknown')
                        connected_nodes.append((conn_id, skill_id, name, stats))
                    else:
                        errors['OrphanedConnection'].append(f"Root node {root_id} connects to invalid node {conn_id}")
                        connected_nodes.append((conn_id, 'Invalid', 'Unknown', {}))
                # Check if connected nodes match expected options
                matched = 0
                for expected_option in expected_options:
                    expected_stats = expected_option['stats']
                    for conn_id, skill_id, name, stats in connected_nodes:
                        if all(k in stats and stats[k] == v for k, v in expected_stats.items()):
                            matched += 1
                            break
                        else:
                            # Log stat mismatch for inspection
                            actual_stats = stats
                            expected_keys = set(expected_stats.keys())
                            actual_keys = set(actual_stats.keys())
                            mismatched_keys = expected_keys - actual_keys
                            if mismatched_keys:
                                stat_mismatches.append(f"Node {conn_id} (skill_id: {skill_id}, name: {name}) for {class_name}: expected stats {expected_stats}, actual stats {actual_stats}, missing keys: {mismatched_keys}")
                if matched == 2:
                    class_start_nodes.append((root_id, group_x, group_y, connected_nodes))
            class_to_start_nodes[class_name] = class_start_nodes
            analysis.append(f"\nClass {class_name} (Location: {class_info['location']})")
            analysis.append(f"Expected starting options: {[{k: v for k, v in option.items() if k != 'name'} for option in expected_options]}")
            analysis.append(f"Expected coordinates: x={x_range}, y={y_range}")
            if class_start_nodes:
                for start_node_id, gx, gy, connected in class_start_nodes:
                    analysis.append(f"Starting node {start_node_id} (group_x={gx:.2f}, group_y={gy:.2f}) connects to:")
                    for conn_id, skill_id, name, stats in connected:
                        analysis.append(f"- Node {conn_id} (skill_id: {skill_id}, name: {name}, stats: {stats})")
            else:
                analysis.append("Root passives (potential starting nodes) for inspection:")
                found = False
                for root_id, root_node in root_passive_nodes:
                    parent = str(root_node.get('parent', 'N/A'))
                    group = groups.get(parent, {})
                    group_x = group.get('x', 0)
                    group_y = group.get('y', 0)
                    position_valid = (x_range[0] <= group_x <= x_range[1]) and (y_range[0] <= group_y <= y_range[1])
                    if position_valid:
                        found = True
                        connections = root_node.get('connections', [])
                        connected_nodes = []
                        for conn in connections:
                            conn_id = str(conn.get('id', ''))
                            if conn_id in node_dict:
                                conn_node = node_dict[conn_id]
                                skill_id = conn_node.get('skill_id', '')
                                skill_details = passive_skills.get(skill_id, {})
                                stats = skill_details.get('stats', {})
                                name = skill_details.get('name', 'Unknown')
                                connected_nodes.append((conn_id, skill_id, name, stats))
                            else:
                                connected_nodes.append((conn_id, 'Invalid', 'Unknown', {}))
                        analysis.append(f"Starting node {root_id} (group_x={group_x:.2f}, group_y={group_y:.2f}) connects to:")
                        for conn_id, skill_id, name, stats in connected_nodes:
                            analysis.append(f"- Node {conn_id} (skill_id: {skill_id}, name: {name}, stats: {stats})")
                if not found:
                    analysis.append(f"No starting nodes found in expected position range.")
                errors['MissingStartingNode'].append(f"No starting nodes found for class {class_name} matching expected options.")
        # Report stat mismatches
        if stat_mismatches:
            analysis.append("\nStat Key Mismatches (for inspection):")
            for mismatch in stat_mismatches[:5]:
                analysis.append(f"- {mismatch}")
        # Check for shared starting locations
        shared_locations = defaultdict(list)
        for class_name, class_info in starting_nodes.items():
            shared_locations[class_info['location']].append(class_name)
        analysis.append("\nShared Starting Locations:")
        for location, classes in shared_locations.items():
            if len(classes) > 1:
                analysis.append(f"- {location}: {', '.join(classes)}")

        # Node 35653 Analysis
        analysis.append("\n=== Node 35653 Analysis ===")
        node_35653 = node_dict.get('35653', {})
        if node_35653:
            skill_id = node_35653.get('skill_id', 'N/A')
            skill_details = passive_skills.get(skill_id, {})
            name = skill_details.get('name', 'Unknown')
            effects = skill_details.get('stats', {})
            parent = node_35653.get('parent', 'N/A')
            position = node_35653.get('position', 0)
            radius = node_35653.get('radius', 0)
            connections = node_35653.get('connections', [])
            group = groups.get(str(parent), {})
            group_x = group.get('x', 0)
            group_y = group.get('y', 0)
            analysis.append(f"Node 35653 details:")
            analysis.append(f"- skill_id: {skill_id}")
            analysis.append(f"- name: {name}")
            analysis.append(f"- effects: {effects}")
            analysis.append(f"- parent group: {parent} (x={group_x:.2f}, y={group_y:.2f})")
            analysis.append(f"- position: {position}, radius: {radius}")
            analysis.append(f"- connections: {connections}")
            # Find other nodes in group 605
            group_605_nodes = [nid for nid, node in node_dict.items() if str(node.get('parent', '')) == '605']
            analysis.append(f"Other nodes in group 605: {len(group_605_nodes)} nodes")
            if group_605_nodes:
                analysis.append("Sample nodes in group 605:")
                for nid in sorted(group_605_nodes)[:5]:
                    node = node_dict[nid]
                    skill_id = node.get('skill_id', 'N/A')
                    skill_details = passive_skills.get(skill_id, {})
                    name = skill_details.get('name', 'Unknown')
                    effects = skill_details.get('stats', {})
                    analysis.append(f"- Node {nid}: skill_id={skill_id}, name={name}, effects={effects}")
            # Find connected node 65468
            connected_node_65468 = node_dict.get('65468', {})
            if connected_node_65468:
                conn_skill_id = connected_node_65468.get('skill_id', 'N/A')
                skill_details = passive_skills.get(conn_skill_id, {})
                conn_name = skill_details.get('name', 'Unknown')
                conn_effects = skill_details.get('stats', {})
                conn_parent = connected_node_65468.get('parent', 'N/A')
                conn_group = groups.get(str(conn_parent), {})
                conn_group_x = conn_group.get('x', 0)
                conn_group_y = conn_group.get('y', 0)
                conn_connections = connected_node_65468.get('connections', [])
                analysis.append(f"Connected node 65468 details:")
                analysis.append(f"- skill_id: {conn_skill_id}")
                analysis.append(f"- name: {conn_name}")
                analysis.append(f"- effects: {conn_effects}")
                analysis.append(f"- parent group: {conn_parent} (x={conn_group_x:.2f}, y={conn_group_y:.2f})")
                analysis.append(f"- connections: {conn_connections}")
                # Check if 65468 connects back to 35653
                connects_back = any(str(conn.get('id', '')) == '35653' for conn in conn_connections)
                analysis.append(f"- Connects back to 35653: {connects_back}")
                if not connects_back:
                    analysis.append("Note: The self-loop on node 35653 is likely a data error, as 65468 does not connect back, and no game mechanic supports self-loops.")
            else:
                analysis.append("Connected node 65468 not found in nodes.")
            # Check for nearby Jewel Sockets
            jewel_sockets_nearby = []
            for nid, node in node_dict.items():
                skill_id = node.get('skill_id', '')
                if 'socket' in skill_id.lower():
                    node_parent = str(node.get('parent', ''))
                    node_group = groups.get(node_parent, {})
                    node_x = node_group.get('x', 0)
                    node_y = node_group.get('y', 0)
                    distance = math.sqrt((node_x - group_x)**2 + (node_y - group_y)**2)
                    if distance < 5000:  # Arbitrary threshold for "nearby"
                        skill_details = passive_skills.get(skill_id, {})
                        name = skill_details.get('name', 'Unknown')
                        effects = skill_details.get('stats', {})
                        jewel_sockets_nearby.append((nid, skill_id, name, effects, node_parent, node_x, node_y, distance))
            analysis.append(f"Jewel Sockets near group 605 (within 5000 units): {len(jewel_sockets_nearby)}")
            if jewel_sockets_nearby:
                analysis.append("Sample nearby Jewel Sockets:")
                for nid, skill_id, name, effects, parent, nx, ny, dist in jewel_sockets_nearby[:5]:
                    analysis.append(f"- Node {nid} (skill_id: {skill_id}, name: {name}, effects: {effects}, group: {parent}, x={nx:.2f}, y={ny:.2f}, distance={dist:.2f})")
        else:
            analysis.append("Node 35653 not found in nodes.")

        # 3. Passive vs. Ascendancy Nodes
        analysis.append("\n=== Passive vs. Ascendancy Nodes ===")
        passive_nodes = {}
        ascendancy_nodes = defaultdict(list)
        ascendancy_sub_variants = defaultdict(list)
        base_class_mapping = {
            'D': ['Druid', 'Duelist'],
            'H': ['Huntress'],
            'M': ['Marauder', 'Mercenary', 'Monk'],
            'R': ['Ranger'],
            'S': ['Shadow', 'Sorceress'],
            'T': ['Templar'],
            'W': ['Warrior', 'Witch']
        }

        for node_id, node in node_dict.items():
            skill_id = node.get('skill_id', '')
            if not skill_id:
                continue
            if skill_id.startswith('Ascendancy'):
                match = re.match(r'Ascendancy(\w+?)(\d+)?(?:\w+)?', skill_id)
                if match:
                    base_class = match.group(1)
                    variant_num = match.group(2) or ''
                    sub_variant = f"{base_class}{variant_num}"
                    variant = sub_variant[0]
                    ascendancy_nodes[variant].append(node_id)
                    ascendancy_sub_variants[sub_variant].append(node_id)
                else:
                    ascendancy_nodes['Unknown'].append(node_id)
                    errors['UnknownAscendancy'].append(f"Node {node_id}: {skill_id}")
            else:
                passive_nodes[node_id] = node

        analysis.append(f"Passive nodes: {len(passive_nodes)}")
        analysis.append(f"Ascendancy nodes: {sum(len(nodes) for nodes in ascendancy_nodes.values())}")
        analysis.append(f"Ascendancy variants: {len(ascendancy_nodes)}")
        analysis.append("Base classes and their full names:")
        for variant, classes in sorted(base_class_mapping.items()):
            analysis.append(f"{variant}: {', '.join(classes)}")
        analysis.append("Note: Marauder, Duelist, Shadow, Templar, and Druid are in development and not currently playable.")

        # Ascendancy Sub-Variants Details
        analysis.append("\nAscendancy Sub-Variants Details")
        for sub_variant in sorted(ascendancy_sub_variants.keys()):
            node_ids = ascendancy_sub_variants[sub_variant]
            start_nodes = [nid for nid in node_ids if 'Start' in node_dict[nid].get('skill_id', '')]
            notable_nodes = [nid for nid in node_ids if passive_skills.get(node_dict[nid].get('skill_id', ''), {}).get('is_notable')]
            small_nodes = [nid for nid in node_ids if 'Small' in node_dict[nid].get('skill_id', '')]
            choice_nodes = [nid for nid in node_ids if passive_skills.get(node_dict[nid].get('skill_id', ''), {}).get('is_multiple_choice')]
            other_nodes = [nid for nid in node_ids if nid not in start_nodes + notable_nodes + small_nodes + choice_nodes]
            start_connections = []
            for nid in start_nodes:
                connections = node_dict[nid].get('connections', [])
                conn_skill_ids = []
                for conn in connections:
                    conn_id = str(conn.get('id', conn))
                    if conn_id in node_dict:
                        conn_skill_id = node_dict[conn_id].get('skill_id', 'N/A')
                        conn_skill_ids.append(conn_skill_id)
                        # Validate ascendancy connections
                        if not conn_skill_id.startswith('Ascendancy') or not conn_skill_id.startswith(f'Ascendancy{sub_variant}'):
                            errors['InvalidAscendancyConnection'].append(f"Start node {nid} ({node_dict[nid].get('skill_id', 'N/A')}) connects to {conn_id} ({conn_skill_id}) outside sub-variant {sub_variant}")
                        elif 'Start' in conn_skill_id:
                            errors['InvalidAscendancyConnection'].append(f"Start node {nid} ({node_dict[nid].get('skill_id', 'N/A')}) connects to another Start node {conn_id} ({conn_skill_id})")
                        elif not ('Small' in conn_skill_id or passive_skills.get(conn_skill_id, {}).get('is_notable')):
                            errors['InvalidAscendancyConnection'].append(f"Start node {nid} ({node_dict[nid].get('skill_id', 'N/A')}) connects to non-Small/non-Notable node {conn_id} ({conn_skill_id})")
                    else:
                        conn_skill_ids.append('Invalid')
                        errors['OrphanedConnection'].append(f"Start node {nid} connects to invalid node {conn_id}")
                start_connections.append((nid, len(connections), node_dict[nid].get('parent', 'N/A'), conn_skill_ids))
            group_counts = defaultdict(int)
            for nid in node_ids:
                group_counts[node_dict[nid].get('parent', 'N/A')] += 1
            analysis.append(f"Sub-Variant {sub_variant}: {len(node_ids)} nodes")
            analysis.append(f"- Start nodes: {len(start_nodes)} (e.g., {start_connections[:5]})")
            analysis.append(f"- Notable nodes: {len(notable_nodes)} (e.g., {notable_nodes[:5]})")
            analysis.append(f"- Small nodes: {len(small_nodes)} (e.g., {small_nodes[:5]})")
            analysis.append(f"- Choice nodes: {len(choice_nodes)} (e.g., {choice_nodes[:5]})")
            analysis.append(f"- Other nodes: {len(other_nodes)} (e.g., {other_nodes[:5]})")
            analysis.append(f"- Groups used: {len(group_counts)} (e.g., {sorted(group_counts.items(), key=lambda x: x[1], reverse=True)[:5]})")
            if not start_nodes:
                errors['NoStartNodes'].append(f"Sub-Variant {sub_variant}: No Start nodes")

        # Split D into Druid and Duelist
        d_nodes = ascendancy_nodes.get('D', [])
        druid_nodes = [nid for nid in d_nodes if node_dict[nid].get('skill_id', '').startswith('AscendancyDruid')]
        duelist_nodes = [nid for nid in d_nodes if node_dict[nid].get('skill_id', '').startswith('AscendancyDuelist')]
        analysis.append("\nD Variant Split")
        analysis.append(f"- Druid nodes: {len(druid_nodes)} (e.g., {druid_nodes[:5]})")
        analysis.append(f"- Duelist nodes: {len(duelist_nodes)} (e.g., {duelist_nodes[:5]})")

        # 4. Connection Data
        analysis.append("\n=== Connection Data ===")
        nodes_with_connections = sum(1 for node in node_dict.values() if node.get('connections', []))
        total_connections = sum(len(node.get('connections', [])) for node in node_dict.values())
        isolated_nodes = len(node_dict) - nodes_with_connections
        analysis.append(f"Nodes with connections: {nodes_with_connections}")
        analysis.append(f"Total connections: {total_connections}")
        analysis.append(f"Isolated nodes: {isolated_nodes}")

        # Connection Validation and Analysis
        analysis.append("\nConnection Validation and Analysis")
        connection_issues = []
        bidirectional_connections = set()
        connection_types = defaultdict(int)
        connections_by_node_type = defaultdict(lambda: defaultdict(int))
        connections_by_sub_variant = defaultdict(lambda: defaultdict(int))
        unidirectional_by_node_type = defaultdict(lambda: defaultdict(int))
        unidirectional_by_group = defaultdict(int)
        self_loops = []
        orphaned_connections = 0
        sample_bidirectional = []
        sample_unidirectional = []
        for node_id, node in node_dict.items():
            skill_id = node.get('skill_id', '')
            parent = str(node.get('parent', 'N/A'))
            is_ascendancy = skill_id.startswith('Ascendancy')
            sub_variant = 'Passive'
            if is_ascendancy:
                match = re.match(r'Ascendancy(\w+?)(\d+)?(?:\w+)?', skill_id)
                if match:
                    sub_variant = f"{match.group(1)}{match.group(2) or ''}"
            node_type = 'Regular'
            if passive_skills.get(skill_id, {}).get('is_notable'):
                node_type = 'Notable'
            elif passive_skills.get(skill_id, {}).get('is_keystone'):
                node_type = 'Keystone'
            elif passive_skills.get(skill_id, {}).get('is_just_icon'):
                node_type = 'Mastery'
            elif 'Start' in skill_id:
                node_type = 'Start'
            elif 'Small' in skill_id:
                node_type = 'Small'
            elif 'socket' in skill_id.lower():
                node_type = 'Jewel Socket'
            connections = node.get('connections', [])
            for conn in connections:
                conn_id = str(conn.get('id', conn))
                conn_radius = conn.get('radius', 0) if isinstance(conn, dict) else 0
                if conn_id == node_id:
                    self_loops.append(f"Node {node_id} ({skill_id}) connects to itself")
                    errors['SelfLoop'].append(f"Node {node_id} ({skill_id})")
                    continue
                if conn_id not in node_dict:
                    connection_issues.append(f"Node {node_id} ({skill_id}) connects to invalid node {conn_id} (radius: {conn_radius})")
                    errors['OrphanedConnection'].append(f"Node {node_id} ({skill_id}) -> {conn_id}")
                    orphaned_connections += 1
                    continue
                conn_skill_id = node_dict[conn_id].get('skill_id', '')
                conn_is_ascendancy = conn_skill_id.startswith('Ascendancy')
                conn_sub_variant = 'Passive'
                if conn_is_ascendancy:
                    conn_match = re.match(r'Ascendancy(\w+?)(\d+)?(?:\w+)?', conn_skill_id)
                    if conn_match:
                        conn_sub_variant = f"{conn_match.group(1)}{conn_match.group(2) or ''}"
                conn_type = passive_skills.get(conn_skill_id, {}).get('is_notable') and 'Notable' or \
                            passive_skills.get(conn_skill_id, {}).get('is_keystone') and 'Keystone' or \
                            passive_skills.get(conn_skill_id, {}).get('is_just_icon') and 'Mastery' or \
                            'Start' in conn_skill_id and 'Start' or \
                            'Small' in conn_skill_id and 'Small' or \
                            'socket' in conn_skill_id.lower() and 'Jewel Socket' or 'Regular'
                if is_ascendancy and conn_is_ascendancy:
                    connection_types['Ascendancy-to-Ascendancy'] += 1
                elif is_ascendancy and not conn_is_ascendancy:
                    connection_types['Ascendancy-to-Passive'] += 1
                elif not is_ascendancy and conn_is_ascendancy:
                    connection_types['Passive-to-Ascendancy'] += 1
                else:
                    connection_types['Passive-to-Passive'] += 1
                connections_by_node_type[node_type][conn_type] += 1
                connections_by_sub_variant[sub_variant][conn_sub_variant] += 1
                conn_connections = [str(c.get('id', c)) for c in node_dict[conn_id].get('connections', [])]
                if node_id in conn_connections:
                    conn_pair = tuple(sorted([node_id, conn_id]))
                    bidirectional_connections.add(conn_pair)
                    if len(sample_bidirectional) < 5:
                        sample_bidirectional.append(f"Node {node_id} ({skill_id}) <-> Node {conn_id} ({conn_skill_id}), radius: {conn_radius}")
                else:
                    connection_issues.append(f"Node {node_id} ({skill_id}) connects to {conn_id} ({conn_skill_id}), radius: {conn_radius}")
                    errors['UnidirectionalConnection'].append(f"Node {node_id} ({skill_id}) -> {conn_id} ({conn_skill_id}), radius: {conn_radius}")
                    unidirectional_by_node_type[node_type][conn_type] += 1
                    unidirectional_by_group[parent] += 1
                    if len(sample_unidirectional) < 5:
                        sample_unidirectional.append(f"Node {node_id} ({skill_id}) -> Node {conn_id} ({conn_skill_id}), radius: {conn_radius}")
        analysis.append(f"Bidirectional connections: {len(bidirectional_connections)}")
        if sample_bidirectional:
            analysis.append("Sample bidirectional connections:")
            for sample in sample_bidirectional:
                analysis.append(f"- {sample}")
        analysis.append(f"Self-loops: {len(self_loops)}")
        if self_loops:
            analysis.append("Sample self-loops:")
            for sample in self_loops[:5]:
                analysis.append(f"- {sample}")
        analysis.append(f"Orphaned connections: {orphaned_connections}")
        analysis.append(f"Connection issues (unidirectional): {len(connection_issues)}")
        if sample_unidirectional:
            analysis.append("Sample unidirectional connection issues:")
            for sample in sample_unidirectional:
                analysis.append(f"- {sample}")
        analysis.append("Unidirectional connections by node type:")
        for node_type, conn_counts in unidirectional_by_node_type.items():
            analysis.append(f"- {node_type}: {dict(conn_counts)}")
        analysis.append("Unidirectional connections by group:")
        top_unidirectional_groups = sorted(unidirectional_by_group.items(), key=lambda x: x[1], reverse=True)[:5]
        for group_id, count in top_unidirectional_groups:
            group = groups.get(group_id, {})
            group_x = group.get('x', 0)
            group_y = group.get('y', 0)
            group_nodes = [nid for nid in node_dict if str(node_dict[nid].get('parent', '')) == group_id]
            sample_nodes = []
            for nid in group_nodes[:5]:
                skill_id = node_dict[nid].get('skill_id', 'N/A')
                skill_details = passive_skills.get(skill_id, {})
                name = skill_details.get('name', 'Unknown')
                effects = skill_details.get('stats', {})
                sample_nodes.append(f"Node {nid} (skill_id: {skill_id}, name: {name}, effects: {effects})")
            analysis.append(f"- Group {group_id} (x={group_x:.2f}, y={group_y:.2f}): {count} unidirectional connections")
            analysis.append(f"  Sample nodes in group: {sample_nodes}")
        analysis.append("Note: The passive skill tree should have bidirectional connections to represent the web-like structure, even though point allocation is one-way (cannot place points backwards on allocated nodes). Unidirectional connections are likely a data error in tree401.json.")

        # Connection Directionality Clarification Needed
        analysis.append("\nConnection Directionality Clarification Needed")
        analysis.append("Note: The passive skill tree is an 'interconnected web,' requiring bidirectional connections in the data to represent all possible paths, even though gameplay mechanics prevent placing points backwards on allocated nodes. The 4384 unidirectional connections are likely a data error.")
        analysis.append(f"Current findings: {len(bidirectional_connections)} bidirectional connections, {len(connection_issues)} unidirectional connections, {len(self_loops)} self-loops.")
        analysis.append("Sample unidirectional connections for inspection:")
        for sample in sample_unidirectional[:5]:
            analysis.append(f"- {sample}")
        analysis.append("Groups with concentrated unidirectional connections (see 'Unidirectional connections by group' above) may indicate specific data errors.")
        if self_loops:
            analysis.append("Additionally, self-loops are noted as data errors (see 'Self-Loop Clarification Needed' below):")
            for sample in self_loops[:5]:
                analysis.append(f"- {sample}")

        # Connection Radius Clarification Needed
        analysis.append("\nConnection Radius Clarification Needed")
        analysis.append("Note: The 'radius' field in connection dictionaries (e.g., -9, 0, 7) likely affects visual path styling or positioning adjustments, particularly for ascendancy nodes in the circular skill tree layout. The value 2147483647 (appearing 33 times) is confirmed as a data error (placeholder for missing values).")
        analysis.append(f"Current findings: {len(outlier_radius_nodes)} connections with radius 2147483647, other values range from -9 to 9.")
        analysis.append("Sample nodes with radius 2147483647 for inspection:")
        for node_id, skill_id, conn_id, conn_skill_id in outlier_radius_nodes[:10]:
            analysis.append(f"- Node {node_id} ({skill_id}) -> Node {conn_id} ({conn_skill_id})")

        # Self-Loop Clarification Needed
        analysis.append("\nSelf-Loop Clarification Needed")
        analysis.append("Note: The self-loop on node 35653 (crossbow9) is treated as a data error, as no game mechanic or wiki information supports self-loops in the skill tree. Its connections are [{'id': '35653', 'radius': 0}, {'id': '65468', 'radius': 0}].")
        analysis.append(f"Current findings: {len(self_loops)} self-loop(s) detected.")
        analysis.append("See 'Node 35653 Analysis' for group details and confirmation of the error.")
        analysis.append("Sample self-loops:")
        for sample in self_loops[:5]:
            analysis.append(f"- {sample}")

        analysis.append("Connection types:")
        for conn_type, count in connection_types.items():
            analysis.append(f"- {conn_type}: {count}")
        analysis.append("Connections by node type:")
        for node_type, conn_counts in connections_by_node_type.items():
            analysis.append(f"- {node_type}: {dict(conn_counts)}")
        analysis.append("Connections by sub-variant:")
        for sub_variant, conn_counts in connections_by_sub_variant.items():
            analysis.append(f"- {sub_variant}: {dict(conn_counts)}")

        # Isolated Nodes Analysis
        analysis.append("\nIsolated Nodes Analysis")
        isolated_node_types = defaultdict(int)
        isolated_by_sub_variant = defaultdict(list)
        for node_id, node in node_dict.items():
            if not node.get('connections', []):
                skill_id = node.get('skill_id', '')
                skill_details = passive_skills.get(skill_id, {})
                node_type = 'Regular'
                if skill_details.get('is_notable'):
                    node_type = 'Notable'
                elif skill_details.get('is_keystone'):
                    node_type = 'Keystone'
                elif skill_details.get('is_just_icon'):
                    node_type = 'Mastery'
                elif skill_details.get('is_multiple_choice'):
                    node_type = 'Choice'
                elif 'Start' in skill_id:
                    node_type = 'Start'
                elif 'Small' in skill_id:
                    node_type = 'Small'
                elif 'socket' in skill_id.lower():
                    node_type = 'Jewel Socket'
                isolated_node_types[node_type] += 1
                sub_variant = 'Passive'
                if skill_id.startswith('Ascendancy'):
                    match = re.match(r'Ascendancy(\w+?)(\d+)?(?:\w+)?', skill_id)
                    if match:
                        sub_variant = f"{match.group(1)}{match.group(2) or ''}"
                isolated_by_sub_variant[sub_variant].append((node_id, skill_id))
        analysis.append("Isolated node types:")
        for node_type, count in sorted(isolated_node_types.items()):
            analysis.append(f"- {node_type}: {count}")
        analysis.append("Isolated nodes by sub-variant:")
        for sub_variant, nodes in sorted(isolated_by_sub_variant.items()):
            analysis.append(f"- {sub_variant}: {len(nodes)} nodes")
            analysis.append(f"  Sample: {nodes[:3]}")

        # 5. Node Types
        analysis.append("\n=== Node Types ===")
        passive_node_types = defaultdict(int)
        ascendancy_node_types = defaultdict(lambda: defaultdict(int))
        for node_id, node in node_dict.items():
            skill_id = node.get('skill_id', '')
            if not skill_id:
                continue
            skill_details = passive_skills.get(skill_id, {})
            node_type = 'Regular'
            if 'Start' in skill_id:
                node_type = 'Start'
            elif 'Small' in skill_id:
                node_type = 'Small'
            elif skill_details.get('is_multiple_choice'):
                node_type = 'Choice'
            elif skill_details.get('is_notable'):
                node_type = 'Notable'
            elif skill_details.get('is_keystone'):
                node_type = 'Keystone'
            elif skill_details.get('is_just_icon'):
                node_type = 'Mastery'
            elif 'socket' in skill_id.lower():
                node_type = 'Jewel Socket'
            if skill_id.startswith('Ascendancy'):
                match = re.match(r'Ascendancy(\w+?)(\d+)?(?:\w+)?', skill_id)
                sub_variant = match.group(1) + (match.group(2) or '') if match else 'Unknown'
                ascendancy_node_types[sub_variant][node_type] += 1
            else:
                passive_node_types[node_type] += 1

        analysis.append("Passive Tree Node Types:")
        for node_type, count in sorted(passive_node_types.items()):
            analysis.append(f"- {node_type}: {count}")
        analysis.append("\nAscendancy Node Types by Sub-Variant:")
        for sub_variant in sorted(ascendancy_node_types.keys()):
            analysis.append(f"Sub-Variant {sub_variant}:")
            for node_type, count in sorted(ascendancy_node_types[sub_variant].items()):
                analysis.append(f"- {node_type}: {count}")

        # 6. Hover Function Fields
        analysis.append("\n=== Hover Function Fields ===")
        skill_id_to_details = passive_skills
        nodes_with_skill_id_mapping = sum(1 for node in node_dict.values() if node.get('skill_id') in skill_id_to_details)
        nodes_with_flavour_text = sum(1 for node in node_dict.values() if node.get('skill_id') in skill_id_to_details and 'flavour_text' in skill_id_to_details[node.get('skill_id')])
        nodes_with_icon = sum(1 for node in node_dict.values() if node.get('skill_id') in skill_id_to_details and 'icon' in skill_id_to_details[node.get('skill_id')])
        nodes_with_ascendancy = sum(1 for node in node_dict.values() if node.get('skill_id') in skill_id_to_details and 'ascendancy' in skill_id_to_details[node.get('skill_id')])
        analysis.append(f"Nodes with skill_id mapped to passive_skills: {nodes_with_skill_id_mapping}")
        analysis.append(f"Nodes with flavour_text: {nodes_with_flavour_text}")
        analysis.append(f"Nodes with icon: {nodes_with_icon}")
        analysis.append(f"Nodes with ascendancy: {nodes_with_ascendancy}")
        if nodes_with_skill_id_mapping:
            analysis.append("Sample nodes with passive_skills mapping:")
            count = 0
            for node in node_dict.values():
                skill_id = node.get('skill_id')
                if skill_id in skill_id_to_details:
                    details = {k: v for k, v in skill_id_to_details[skill_id].items() if k in ['name', 'stats', 'is_notable', 'is_keystone', 'is_just_icon', 'is_multiple_choice', 'icon', 'ascendancy']}
                    analysis.append(f"Node {skill_id}: {details}")
                    count += 1
                    if count >= 5:
                        break

        # 7. Summary
        analysis.append("\n=== Summary ===")
        analysis.append(f"Total nodes: {len(node_dict)} (Passive: {len(passive_nodes)}, Ascendancy: {sum(len(nodes) for nodes in ascendancy_nodes.values())})")
        analysis.append(f"Total connections: {total_connections} (Bidirectional: {len(bidirectional_connections)}, Self-loops: {len(self_loops)}, Issues: {len(connection_issues)})")
        analysis.append(f"Errors detected: {sum(len(v) for v in errors.values())}")
        if errors:
            analysis.append("Error summary:")
            for error_type, error_list in errors.items():
                analysis.append(f"- {error_type}: {len(error_list)} errors")
                if error_list:
                    analysis.append(f"  Sample: {error_list[:3]}")
        if outlier_radius_nodes:
            analysis.append("Warning: Connections with radius 2147483647 indicate data errors. See 'Connection Radius Clarification Needed'.")
        if connection_issues:
            analysis.append("Warning: High unidirectional connections indicate a data error in tree401.json. See 'Connection Directionality Clarification Needed'.")
        if self_loops:
            analysis.append("Warning: Self-loops detected, treated as data errors. See 'Self-Loop Clarification Needed'.")
        if ambiguous_references:
            analysis.append("Warning: Ambiguous group references due to ID overlaps may cause issues.")

        # Write analysis to file
        with open(output_file, 'w') as f:
            f.write("\n".join(analysis))
        log_message(logging.INFO, 'FILE', f"Analysis written to {output_file}")

    except Exception as e:
        log_message(logging.ERROR, 'GENERAL', f"Error analyzing {json_file}: {str(e)}")
        raise

def main():
    json_file = '../tree401.json'
    if not os.path.exists(json_file):
        log_message(logging.ERROR, 'FILE', f"Error: {json_file} not found in current directory.")
        return
    analyze_tree401(json_file)

if __name__ == '__main__':
    main()