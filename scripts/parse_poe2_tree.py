import json
import os
import logging
from collections import defaultdict

# Configure logging
default_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=default_format)
logger = logging.getLogger(__name__)

def parse_poe2_tree(input_file: str, output_file: str):
    """
    Parse tree401.json to extract all data needed for GUI mapping of the PoE2 passive skill tree.
    Outputs a consolidated skill_tree_data.json with groups, nodes (including metadata and connections), and root_passives.
    """
    # Ensure output directory exists
    out_dir = os.path.dirname(output_file)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"Created output directory: {out_dir}")

    # Load raw data
    logger.info(f"Loading tree data from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    passive_tree = data.get('passive_tree', {})
    passive_skills = data.get('passive_skills', {})

    # Extract groups
    groups = {}
    for gid, g in passive_tree.get('groups', {}).items():
        groups[str(gid)] = {
            'x': g.get('x'),
            'y': g.get('y'),
            'bg': g.get('bg'),
            'proxy': g.get('proxy'),
            'unk2': g.get('unk2')
        }

    # Extract and clean nodes
    raw_nodes = passive_tree.get('nodes', {})
    nodes = {}
    # 1) Remove self-loops and clamp outlier radii in connections
    for nid, node in raw_nodes.items():
        nid_str = str(nid)
        # Base node info
        skill_id = node.get('skill_id')
        parent = node.get('parent')
        position = node.get('position')
        radius = node.get('radius')
        # Clean connections
        cleaned_conns = []
        for c in node.get('connections', []):
            if isinstance(c, dict):
                cid = str(c.get('id'))
                crad = c.get('radius', 0)
            else:
                cid = str(c)
                crad = 0
            # Drop self-loop
            if cid == nid_str:
                continue
            # Clamp placeholder radius
            if crad == 2147483647:
                crad = 0
            cleaned_conns.append({'id': cid, 'radius': crad})
        nodes[nid_str] = {
            'skill_id': skill_id,
            'parent': str(parent),
            'position': position,
            'radius': radius,
            'connections': cleaned_conns
        }

    # 2) Mirror connections to make the graph undirected
    for nid, node in nodes.items():
        for conn in node['connections']:
            cid = conn['id']
            if cid in nodes:
                # Check if reverse link exists
                reverse = nodes[cid]['connections']
                if not any(rc['id'] == nid for rc in reverse):
                    reverse.append({'id': nid, 'radius': conn['radius']})

    # 3) Enrich nodes with skill metadata and type
    for nid, node in nodes.items():
        skill_id = node['skill_id'] or ''
        details = passive_skills.get(skill_id, {})
        # Metadata
        node['name'] = details.get('name')
        node['stats'] = details.get('stats', {})
        node['icon'] = details.get('icon')
        node['ascendancy'] = details.get('ascendancy')
        node['is_notable'] = details.get('is_notable', False)
        node['is_keystone'] = details.get('is_keystone', False)
        node['is_multiple_choice'] = details.get('is_multiple_choice', False)
        # Determine node type for rendering
        if skill_id.startswith('Ascendancy'):
            ntype = 'Ascendancy'
        elif details.get('is_keystone'):
            ntype = 'Keystone'
        elif details.get('is_notable'):
            ntype = 'Notable'
        elif details.get('is_just_icon'):
            ntype = 'Mastery'
        elif 'socket' in skill_id.lower():
            ntype = 'Jewel Socket'
        elif 'Start' in skill_id:
            ntype = 'Start'
        elif 'Small' in skill_id:
            ntype = 'Small'
        else:
            ntype = 'Regular'
        node['node_type'] = ntype

    # Extract root passives
    root_passives = [str(rp) for rp in passive_tree.get('root_passives', [])]

    # Consolidate output
    output_data = {
        'groups': groups,
        'nodes': nodes,
        'root_passives': root_passives
    }

    # Write to skill_tree_data.json
    logger.info(f"Writing parsed data to {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    logger.info("Parsing complete.")

if __name__ == '__main__':
    INPUT_FILE = '../data/tree401.json'
    OUTPUT_FILE = r'/output/skill_tree_data.json'
    parse_poe2_tree(INPUT_FILE, OUTPUT_FILE)
