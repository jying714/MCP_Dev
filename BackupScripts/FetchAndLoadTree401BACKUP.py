import requests
import json

url = "https://assets-ng.maxroll.gg/poe2planner/game/tree401.json?0dce6a5f"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    with open("tree401.json", "w") as f:
        json.dump(data, f, indent=2)  # Save locally for inspection
    print("JSON loaded successfully")
except requests.RequestException as e:
    print(f"Error fetching JSON: {e}")
    exit(1)