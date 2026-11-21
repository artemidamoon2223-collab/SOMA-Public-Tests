import itertools
import json
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "open019"), str(ROOT / "probes018")]
import trial as parent
from policy import decide


def measure(root, key, catalogue, allowed):
    inventory = sorted(p.name for p in root.glob("*.json"))
    ordinary = parent.launch(root, "app.py")
    witness = parent.launch(root, ROOT / "trim017/observe_trim.py")
    trace = []

    def probe(name):
        if name not in allowed or len(trace) >= 2 or any(prev == name for prev, _ in trace):
            raise RuntimeError("probe scope")
        output = parent.edit_launch(root, name, "planner")
        trace.append([name, output])
        return output != ordinary

    decision = decide(catalogue, inventory, allowed, probe)
    oracle = {f: parent.edit_launch(root, f, "oracle") for f in inventory}
    print("CASE", json.dumps([key, ordinary, witness, inventory, trace, decision, oracle]), flush=True)


def historical():
    for label, access, index in itertools.product(parent.CATALOGUES, ("open", "one"), range(8)):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parent.fixture(root, parent.UNIVERSE[index])
            allowed = parent.FILES if access == "open" else parent.FILES[:1]
            measure(root, [label, access, index], parent.CATALOGUES[label], allowed)


def controls():
    files = parent.FILES[:2]
    sets = [list(s) for n in range(3) for s in itertools.combinations(files, n)]
    for index, active in enumerate(sets):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parent.fixture(root, active)
            # Construct a genuine two-input control. The extra fixture file has
            # no consumers in these programs and is absent from their inventory.
            (root / parent.FILES[2]).unlink()
            measure(root, ["control", index], [files[:1], files[1:]], files)


if __name__ == "__main__":
    print("COMMIT", os.environ["SOURCE_SHA"], flush=True)
    historical()
    controls()
