import base64
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
from policy import investigate

KNOWN = ("defaults.json", "profile.json")
ARMS = ("closed", "expand_on_contradiction", "verify_known", "inspect_first")
APP = """import json
from pathlib import Path
def read(name):
    return json.loads(Path(name).read_bytes())
exec(compile(Path("loader.py").read_text(), "loader.py", "exec"))
print(json.dumps(settings["limit"]))
"""


def start(root):
    run = subprocess.run([sys.executable, "-I", "-B", "app.py"], cwd=root,
                         text=True, capture_output=True, timeout=3)
    if run.returncode or run.stderr:
        raise RuntimeError(run.stderr)
    return json.loads(run.stdout)


def write(path, value):
    path.write_text(json.dumps(value))


def trial(root, known, baseline, arm):
    allowed = set(KNOWN)
    log = []
    def inspect():
        if len(log) >= 2:
            raise ValueError("budget")
        source = (root / "loader.py").read_text()
        # Only grant names occurring literally in this fixture's source.
        import ast
        allowed.update(n.value for n in ast.walk(ast.parse(source))
                       if isinstance(n, ast.Constant) and type(n.value) is str)
        log.append(["read", source])
        return source
    def probe(path):
        if len(log) >= 2 or path not in allowed:
            raise ValueError("probe scope")
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "clone"
            shutil.copytree(root, clone)
            doc = json.loads((clone / path).read_bytes())
            if "limit" in doc:
                doc["limit"] = 91
                write(clone / path, doc)
                result = start(clone)
            else:
                result = "no_key"
        log.append(["probe", path, result])
        return result
    return [investigate(arm, known, baseline, inspect, probe), log]


def run(root):
    (root / "app.py").write_text(APP)
    rows = []
    for i, (rev, d, p, state) in enumerate(itertools.product(
            (0, 1), (0, 7), (0, 7), ("unused", "empty", "zero", "seven", "eleven"))):
        saved = ("session.json", "snapshot.json")[i % 2]
        paths = list(reversed(KNOWN)) if rev else list(KNOWN)
        if state != "unused":
            paths.append(saved)
        source = "settings = " + " | ".join("read(" + repr(path) + ")" for path in paths) + "\n"
        (root / "loader.py").write_text(source)
        known = dict(zip(KNOWN, (d, p)))
        for path, value in known.items():
            write(root / path, {"limit": value})
        value = {"empty": None, "zero": 0, "seven": 7, "eleven": 11, "unused": 11}[state]
        write(root / saved, {} if value is None else {"limit": value})
        baseline = start(root)
        with tempfile.TemporaryDirectory() as tmp:
            oracle = Path(tmp) / "oracle"
            shutil.copytree(root, oracle)
            for marker, path in enumerate((*KNOWN, saved), start=81):
                if "limit" in json.loads((oracle / path).read_bytes()):
                    write(oracle / path, {"limit": marker})
            tagged = start(oracle)
        rows.append([baseline, tagged, [trial(root, known, baseline, arm) for arm in ARMS]])
        (root / saved).unlink()
    return rows


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        raw = json.dumps(run(Path(tmp)), separators=(",", ":")).encode()
    print(json.dumps(dict(sha=os.environ["SOURCE_SHA"], rows=base64.b64encode(zlib.compress(raw)).decode())))
