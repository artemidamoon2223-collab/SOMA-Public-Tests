"""Frozen CI-018 planner, executed on public incomplete catalogues."""
from itertools import combinations, product
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "probes018"))
from choose import investigate
from run import launch, edit_launch

FILES = ["a.json", "b.json", "c.json"]
UNIVERSE = [list(s) for n in range(4) for s in combinations(FILES, n)]
CATALOGUES = {"two_names": [["a.json"], ["b.json"], ["a.json", "b.json"]],
              "nonempty": UNIVERSE[1:]}


def fixture(root, active):
    for name in FILES:
        (root / name).write_text(json.dumps({"value": "seed"}))
    # All truth assignments have identical baseline output. A one-file edit
    # reveals membership only, including when the active source set is empty.
    code = ("import json\nfrom pathlib import Path\n"
            f"sources = {active!r}\n"
            "v = [json.loads(Path(p).read_text())['value'] for p in sources]\n"
            "print(json.dumps(next((s.upper() for s in v if s != 'seed'), 'BASE')))\n")
    (root / "app.py").write_text(code)


def evaluate(root, label, access, index):
    names = FILES if access == "open" else FILES[:1]
    family = CATALOGUES[label]
    baseline = launch(root, "app.py")
    witness = launch(root, ROOT / "trim017/observe_trim.py")
    trace = []

    def probe(name):
        if name not in names or len(trace) >= 2 or any(n == name for n, _ in trace):
            raise ValueError("access or budget")
        observed = edit_launch(root, name, "planner")
        trace.append([name, observed])
        return baseline != observed

    answer = investigate(family, names, probe, adaptive=True)
    # A separate diagnostic runs on an independent copy after the decision.
    # The policy never sees its result. Only use the open-access cohort.
    challenge = None
    if label == "two_names" and access == "open":
        challenge = [FILES[-1], edit_launch(root, FILES[-1], "control")]
    oracle = {n: edit_launch(root, n, "oracle") for n in FILES}
    return [[label, access, index], baseline, witness, trace, answer, challenge, oracle]


if __name__ == "__main__":
    print("COMMIT", os.environ["SOURCE_SHA"], flush=True)
    for (label, access), (index, active) in product(product(CATALOGUES, ("open", "one")), enumerate(UNIVERSE)):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root, active)
            print("CASE", json.dumps(evaluate(root, label, access, index)), flush=True)
