"""Independent integer-bit oracle. No experiment or policy imports."""
import collections
import hashlib
import json
from pathlib import Path
import sys


def audit(report, commit):
    root = Path(__file__).resolve().parent.parent
    paths = ["selection006/select_probe.py", "selection006/experiment.py", "selection006/audit.py",
             ".github/workflows/soma-selection-006.yml"]
    if report["commit"] != commit or report["hashes"] != {
        p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths
    }:
        raise ValueError("provenance")
    rows = report["rows"]
    if len(rows) != 1024:
        raise ValueError("coverage")
    counts = [collections.Counter(), collections.Counter()]
    for n in range(512):
        pair, variant = divmod(n, 8)
        first, second = divmod(pair, 8)
        truth, mode = divmod(variant, 4)
        lost, strategy = divmod(mode, 2)
        diff = first ^ second
        channel = 3 - diff.bit_length() if strategy and diff else 0
        unique = bool(diff & (4 >> channel))
        expected = str(truth) if unique and not lost else "?"
        if rows[2*n:2*n+2] != str(channel) + expected:
            raise ValueError("decision")
        counts[strategy]["correct" if expected != "?" else "abstain"] += 1
    return counts


if __name__ == "__main__":
    report = json.loads(Path(sys.argv[1]).read_bytes())
    counts = audit(report, sys.argv[2])
    for replacement, reason in [(report["rows"][:-2], "coverage"), ("00"+report["rows"][2:], "decision")]:
        try:
            audit(dict(report, rows=replacement), sys.argv[2])
        except ValueError as e:
            if str(e) != reason:
                raise
        else:
            raise ValueError("corrupt report accepted")
    print("AUDIT", json.dumps(dict(fixed=counts[0], separating=counts[1], corrupt_rejected=2)))
