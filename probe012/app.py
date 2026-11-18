"""Run in a fixture directory with one of two loader implementations."""
import json
from pathlib import Path
from loader import merge


def read(name):
    return json.loads(Path(name + ".json").read_text())


profile = read("launch")["profile"]
layers = read(profile) if profile else {}
print(json.dumps(merge(read("defaults"), layers).get("limit")))
