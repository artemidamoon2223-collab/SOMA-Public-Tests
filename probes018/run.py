import itertools
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from choose import investigate


def launch(root, script):
    p = subprocess.run([sys.executable, "-I", "-B", str(script)], cwd=root, text=True,
                       capture_output=True, timeout=4, check=True)
    if p.stderr:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def edit_launch(root, name, marker):
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "copy"
        shutil.copytree(root, clone)
        path = clone / name
        doc = json.loads(path.read_text())
        doc["value"] = marker
        path.write_text(json.dumps(doc))
        return launch(clone, "app.py")


def trial(root, key, names, family, allowed):
    ordinary = launch(root, "app.py")
    witness = launch(root, ROOT / "trim017/observe_trim.py")
    if witness != {"stdout": json.dumps(ordinary) + "\n", "sinks": [[None, ordinary]]}:
        raise ValueError("missing label-loss trigger")
    records = []
    for adaptive in (False, True):
        trace = []
        def probe(name):
            if len(trace) >= 2 or name not in allowed or any(item[0] == name for item in trace):
                raise ValueError("unauthorized probe")
            observed = edit_launch(root, name, "Z")
            trace.append([name, observed])
            return observed != ordinary
        answer = investigate(family, allowed, probe, adaptive)
        records.append([trace, answer])
    oracle = {name: edit_launch(root, name, "Q") for name in names}
    print("CASE", json.dumps([key, ordinary, witness, names, family, allowed, records, oracle]), flush=True)


def old_cases():
    # Reuse the exact builder. Suppress its previous oracle runs and evaluate
    # only its six recorded abstentions, after the builder restores both files.
    builder = runpy.run_path(str(ROOT / "trim017/trial.py"))["fresh"]
    def measure(root, key, _):
        if key[0] in ("two_files", "join", "upper"):
            names = ["left.json", "right.json"]
            family = [list(s) for n in range(3) for s in itertools.combinations(names, n)]
            trial(root, ["old", *key], names, family, names)
    with patch.dict(builder.__globals__, {"execute": lambda *_: None, "measure": measure}):
        builder()


def new_cases():
    filenames = ["ash.json", "bay.json", "elm.json", "oak.json"]
    for shift in (0, 2):
        names = filenames[shift:] + filenames[:shift]
        a, b, c, d = names
        full = [[a], [a, b], [c], [d]]
        for style, family, allowed in [("fork", full, names), ("early", full[:3], names),
                                        ("restricted", full, [a]), ("denied", full, [])]:
            for variant, sources in enumerate(family):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    for name in names:
                        (root / name).write_text(json.dumps({"value": "x"}))
                    selected = sources if len(sources) > 1 else sources * 2
                    program = ("import json\nfrom pathlib import Path\n"
                               f"names = {selected!r}\n"
                               "parts = [json.loads(Path(n).read_text())['value'] for n in names]\n"
                               "print(json.dumps(''.join(parts).upper()))\n")
                    (root / "app.py").write_text(program)
                    trial(root, ["new", shift, style, variant], names, family, allowed)


if __name__ == "__main__":
    print("COMMIT", os.environ["SOURCE_SHA"], flush=True)
    old_cases()
    new_cases()
