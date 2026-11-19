"""Paired environments for the frozen CI-014 policy and evidence adapter."""
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine

FILES = ("defaults.json", "boot.json")
RULES = [("inspect", "unresolved"), ("inspect", "always")]


def build(spec):
    value, spelling, active, _ = spec
    path = '"boot.json"' if spelling == "literal" else 'Path("boot").with_suffix(".json")'
    source = f"""import json
from pathlib import Path
def read(path):
    return json.loads(Path(path).read_text())
value = read("defaults.json")["value"]
layer = read({path})
if layer["enabled"]:
    value = layer["value"]
print(json.dumps(value))
"""
    return source, [{"value": value}, {"enabled": active, "value": value}]


def replace(path, marker):
    data = json.loads(path.read_bytes())
    data["value"] = marker
    path.write_text(json.dumps(data))
    return True


def main():
    print("COMMIT", os.environ["SOURCE_SHA"], flush=True)
    for spec in itertools.product(("amber", "teal"), ("literal", "computed"),
                                  (False, True), ("open", "no_probes")):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = engine.run_case(root, sys.modules[__name__], spec, RULES)
            print("CASE", json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
