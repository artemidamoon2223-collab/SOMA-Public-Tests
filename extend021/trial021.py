"""Use recorded CI-020 observations once, then fork the identical request."""
import json
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "open019"), str(ROOT / "probes018")]
import trial as fixture
from extension import prepare, finish


def exercise(raw):
    key, baseline, _, files, trace, _, _ = raw
    prefix = [(f, output != baseline) for f, output in trace]
    initial, target = prepare(files, prefix)
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # CI-020 controls have two inputs, and the historical three-input
        # scenarios use the original builder and original fixture selection.
        if key[0] == "control":
            subsets = [[], files[:1], files[1:], files]
            fixture.fixture(root, subsets[key[1]])
            (root / "c.json").unlink()
        else:
            fixture.fixture(root, fixture.UNIVERSE[key[-1]])
        if sorted(p.name for p in root.glob("*.json")) != files or fixture.launch(root, "app.py") != baseline:
            raise ValueError("fixture drift")
        for mode in ("deny", "allow"):
            log = []
            def probe(name):
                if mode != "allow" or target is None or name != target or log or name not in files:
                    raise ValueError("worker scope")
                observed = fixture.edit_launch(root, name, "extension")
                log.append([name, observed])
                return observed != baseline
            final = finish(files, prefix, target, mode == "allow", probe)
            results[mode] = [log, final]
    return [key, initial, target, results]


if __name__ == "__main__":
    history = json.loads((ROOT / "refute020/EVIDENCE.json").read_bytes())
    print("COMMIT", os.environ["SOURCE_SHA"], flush=True)
    for row in history["records"][1:]:
        print("CASE", json.dumps(exercise(json.loads(row[5:]))), flush=True)
