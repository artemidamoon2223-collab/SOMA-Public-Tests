"""Deterministic public engineering fixture, without training or a hidden holdout."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
from select_probe import choose, conclude

words = list(itertools.product((0, 1), repeat=3))
rows = []
for first, second in itertools.product(words, repeat=2):
    models = (first, second)
    # Freeze choices before truth or delivery is selected.
    choices = [choose(models, policy) for policy in ("fixed", "separating")]
    for truth in (0, 1):
        for withheld in (False, True):
            for index in choices:
                answer = None if withheld else models[truth][index]
                decision = conclude(models, index, answer)
                rows.append(str(index) + ("?" if decision is None else str(decision)))
files = ["selection006/select_probe.py", "selection006/experiment.py", "selection006/audit.py",
         ".github/workflows/soma-selection-006.yml"]
print(json.dumps(dict(commit=os.environ["SOURCE_SHA"], rows="".join(rows),
                      hashes={f: hashlib.sha256((root.parent / f).read_bytes()).hexdigest() for f in files})))
