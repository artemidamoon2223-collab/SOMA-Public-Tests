import itertools
import json

FILES = ("base.json", "layer.json")


def cases():
    return itertools.product(("zero", "seven"), (False, True), (None, "zero", "seven"), ("open", "opaque"))


def build(spec):
    default, enabled, override, _ = spec
    code = """import json
from pathlib import Path
def load(path):
    return json.loads(Path(path).read_bytes())
config = load("base.json")
"""
    if enabled:
        code += 'config.update(load("layer.json"))\n'
    return code + 'print(json.dumps(config["value"]))\n', [
        {"value": default}, {} if override is None else {"value": override}]


def replace(path, marker):
    doc = json.loads(path.read_bytes())
    if "value" not in doc:
        return False
    path.write_text(json.dumps({"value": marker}))
    return True
