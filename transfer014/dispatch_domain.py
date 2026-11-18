import itertools
import json

FILES = ("routing.json", "events.json")


def cases():
    return itertools.product(("mail", "batch"), (False, True),
                             ("empty", "old", "mail", "batch", "other"), ("open", "no_probes", "opaque"))


def build(spec):
    configured, restart, state, _ = spec
    code = """import json
from pathlib import Path
def read(path):
    return json.loads(Path(path).read_bytes())
queue = read("routing.json")["queue"]
"""
    if restart:
        code += '''for event in read("events.json"):
    if event["kind"] == "resume":
        queue = event["destination"]
'''
    events = [] if state == "empty" else [{"kind": "note", "destination": "unused"}]
    if state not in ("empty", "old"):
        events.extend([{"kind": "resume", "destination": "superseded"},
                       {"kind": "resume", "destination": state},
                       {"kind": "note", "destination": "ignore"}])
    return code + "print(json.dumps(queue))\n", [{"queue": configured}, events]


def replace(path, marker):
    data = json.loads(path.read_bytes())
    if isinstance(data, dict):
        data["queue"] = marker
    else:
        for event in reversed(data):
            if event["kind"] == "resume":
                event["destination"] = marker
                break
        else:
            return False
    path.write_text(json.dumps(data))
    return True
