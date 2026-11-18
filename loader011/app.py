"""Synthetic application: run from a directory containing the three JSON files and loader.py."""
import json
from pathlib import Path
from loader import merge


def read(name):
    return json.loads(Path(name).read_text())


defaults = read("defaults.json")
profile = read("green.json") if read("launch.json")["enabled"] else {}
print(json.dumps(merge(defaults, profile).get("limit")))
