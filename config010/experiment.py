import base64
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from policies import investigate

FILES = ["defaults.json", "launch.json", "blue.json", "green.json"]
POLICIES = ["defaults_only", "fixed", "adaptive"]


def execute(root):
    p = subprocess.run([sys.executable, "-I", "-B", str(HERE / "app.py")], cwd=root,
                       capture_output=True, text=True, timeout=2)
    if p.returncode != 0 or p.stderr:
        raise RuntimeError("application failed")
    return int(p.stdout)


def write(root, name, content):
    (root / name).write_text(json.dumps(content))


def trial(root, policy, blocked):
    trace = []
    def read(name):
        if len(trace) >= 3 or name not in FILES or any(r[0] == name for r in trace):
            raise ValueError("invalid investigation")
        obj = None if name == blocked else json.loads((root / name).read_bytes())
        trace.append([name, obj])
        return obj
    return [investigate(policy, read), trace]


def run(root):
    cases = []
    for default, profile, blue, green in itertools.product((0, 7), (None, "blue", "green"),
                                                           (None, 0, 7), (None, 0, 7)):
        docs = [{"limit": default}, {"profile": profile},
                {} if blue is None else {"limit": blue}, {} if green is None else {"limit": green}]
        for name, doc in zip(FILES, docs):
            write(root, name, doc)
        value = execute(root)
        # Change each existing definition alone. Preserve absent keys and the launch selection.
        perturbed = {}
        for name, doc in zip(FILES, docs):
            if "limit" in doc:
                write(root, name, {"limit": 91})
                perturbed[name] = execute(root)
                write(root, name, doc)
        cases.append([value, perturbed, [[trial(root, p, blocked) for p in POLICIES]
                                          for blocked in [None, *FILES]]])
    return cases


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        data = json.dumps(run(Path(tmp)), separators=(",", ":")).encode()
    print(json.dumps({"sha": os.environ["SOURCE_SHA"],
                      "cases": base64.b64encode(zlib.compress(data, 9)).decode()}))
