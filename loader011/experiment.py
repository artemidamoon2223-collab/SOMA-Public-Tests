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
from policy import investigate

SOURCES = ["def merge(defaults, profile):\n    return defaults | profile\n",
           "def merge(defaults, profile):\n    return profile | defaults\n"]
FILES = ["loader.py", "defaults.json", "launch.json", "green.json"]


def execute(root):
    # Isolated mode drops script directory; add only this controlled fixture directory.
    code = "import sys,runpy; sys.path.insert(0,'.'); runpy.run_path('app.py')"
    p = subprocess.run([sys.executable, "-I", "-B", "-c", code], cwd=root, text=True,
                       capture_output=True, timeout=2)
    if p.returncode or p.stderr:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def collect(root, blocked, eager):
    trace = []
    def read(name):
        if name not in FILES or name in [row[0] for row in trace] or len(trace) >= 4:
            raise ValueError("read budget")
        if name == "loader.py":
            value = None if blocked else (root / name).read_text()
        else:
            value = json.loads((root / name).read_bytes())
        trace.append([name, value])
        return value
    return [investigate(read, eager), trace]


def run(root):
    (root / "app.py").write_bytes((HERE / "app.py").read_bytes())
    cases = []
    for source, active, default, green in itertools.product(SOURCES, (False, True), (None, 0, 7), (None, 0, 7)):
        (root / "loader.py").write_text(source)
        docs = {"defaults.json": {} if default is None else {"limit": default},
                "green.json": {} if green is None else {"limit": green}, "launch.json": {"enabled": active}}
        for name, doc in docs.items():
            (root / name).write_text(json.dumps(doc))
        output = execute(root)
        probes = {}
        for name, doc in docs.items():
            if "limit" in doc:
                (root / name).write_text('{"limit":91}')
                probes[name] = execute(root)
                (root / name).write_text(json.dumps(doc))
        cases.append([output, probes, [collect(root, blocked, eager) for blocked in (False, True)
                                      for eager in (True, False)]])
    return cases


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        raw = json.dumps(run(Path(tmp)), separators=(",", ":")).encode()
    print(json.dumps({"commit": os.environ["SOURCE_SHA"],
                      "cases": base64.b64encode(zlib.compress(raw, 9)).decode()}))
