import base64
import copy
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from policy import POLICIES, investigate

FILES = ("defaults", "blue", "green")
SENTINELS = (84, 85, 86)


def write(path, obj):
    path.write_text(json.dumps(obj))


def start(path):
    code = "import sys, runpy; sys.path.insert(0,'.'); runpy.run_path('app.py')"
    proc = subprocess.run([sys.executable, "-I", "-B", "-c", code], cwd=path,
                          capture_output=True, text=True, timeout=3)
    if proc.returncode or proc.stderr:
        raise RuntimeError(proc.stderr)
    return json.loads(proc.stdout)


def snapshot(path):
    return {p.name: p.read_bytes() for p in path.iterdir()}


def trial(original, config, baseline, policy):
    receipts = []
    def probe(name):
        if receipts or name not in FILES:
            raise ValueError("invalid intervention")
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "app"
            shutil.copytree(original, clone)
            before = snapshot(clone)
            path = clone / (name + ".json")
            write(path, {"limit": 91})
            after = snapshot(clone)
            if before.keys() != after.keys() or [k for k in before if before[k] != after[k]] != [path.name]:
                raise ValueError("edit scope")
            result = start(clone)
            receipts.append([name, result])
            return result
    answer = investigate(copy.deepcopy(config), baseline, policy, probe)
    return [receipts, answer]


def main():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "app.py").write_bytes((HERE / "app.py").read_bytes())
        for expr, active, d, b, g in itertools.product(
                ("defaults | profile", "profile | defaults"), (None, "blue", "green"),
                (None, 0, 7), (None, 0, 7), (None, 0, 7)):
            (root / "loader.py").write_text("def merge(defaults, profile):\n    return " + expr + "\n")
            config = {"launch": {"profile": active}}
            for name, value in zip(FILES, (d, b, g)):
                config[name] = {} if value is None else {"limit": value}
            for name, obj in config.items():
                write(root / (name + ".json"), obj)
            before = snapshot(root)
            baseline = start(root)
            with tempfile.TemporaryDirectory() as separate:
                oracle = Path(separate) / "app"
                shutil.copytree(root, oracle)
                for name, marker in zip(FILES, SENTINELS):
                    if "limit" in config[name]:
                        write(oracle / (name + ".json"), {"limit": marker})
                tagged = start(oracle)
            trials = [trial(root, config, baseline, p) for p in POLICIES]
            if snapshot(root) != before:
                raise ValueError("original modified")
            rows.append([baseline, tagged, trials])
    compressed = zlib.compress(json.dumps(rows, separators=(",", ":")).encode(), 9)
    print(json.dumps({"sha": os.environ["SOURCE_SHA"], "rows": base64.b64encode(compressed).decode()}))


if __name__ == "__main__":
    main()
