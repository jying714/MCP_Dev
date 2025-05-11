import json
import requests
from typing import List, Optional


def save_to_maxroll(
    node_list: List[int],
    version_id: int,
    char_class: str,
    ascendancy: str,
    name: Optional[str] = None,
    public: bool = False,
    folder: int = 0
) -> str:
    """
    Save a PoB-imported build to Maxroll and return its shareable URL.

    - node_list: allocated passive node IDs
    - version_id: passive tree version (e.g. 401)
    - char_class: Maxroll charClass string (e.g. "DexFour")
    - ascendancy: Maxroll ascendancy string (e.g. "Deadeye")
    - name: optional build name
    - public: whether the build is public (True) or private (False)
    - folder: folder ID to save under (0 for root)

    Returns:
        Full Maxroll URL: https://maxroll.gg/poe2/passive-tree/{build_id}
    """
    session = requests.Session()
    # Seed any cookies by visiting the import page
    session.get("https://maxroll.gg/poe2/pob/")

    build_name = name or f"{char_class} {ascendancy} Build"
    # Construct the JSON-stringified data payload for PoB import
    tree_payload = {
        "passive_tree": {
            "version": version_id,
            "charClass": char_class,
            "ascendancy": ascendancy,
            "variants": [{
                "history": node_list,
                "masteries": {},
                "jewels": {},
                "attributes": {},
                "notes": []
            }],
            "active": 0
        }
    }
    payload = {
        "data": json.dumps(tree_payload, separators=(",", ":")),
        "name": build_name,
        "public": int(public),
        "folder": folder,
        "type": "pob"
    }

    headers = {
        "Content-Type": "application/json",
        "Origin": "https://maxroll.gg",
        "Referer": "https://maxroll.gg/poe2/pob/",
    }

    resp = session.post(
        "https://planners.maxroll.gg/profiles/poe2",
        json=payload,
        headers=headers,
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    build_id = data.get("id")
    if not build_id:
        raise RuntimeError(f"Failed to save build: {data}")

    return f"https://maxroll.gg/poe2/passive-tree/{build_id}"
