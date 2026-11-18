"""Finite-world oracle for value and causal source; no strategy imports."""
import base64
from collections import Counter, defaultdict
import copy
import itertools
import json
from pathlib import Path
import sys
import zlib


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def universe():
    for override, enabled, d, p in itertools.product((True, False), (False, True), (None, 0, 7), (None, 0, 7)):
        expression = "defaults | profile" if override else "profile | defaults"
        docs = {"loader.py": "def merge(defaults, profile):\n    return " + expression + "\n",
                "launch.json": {"enabled": enabled}, "defaults.json": {} if d is None else {"limit": d},
                "green.json": {} if p is None else {"limit": p}}
        winner = (None, None)
        if enabled and p is not None and (override or d is None):
            winner = (p, "green.json")
        elif d is not None:
            winner = (d, "defaults.json")
        yield docs, winner, enabled and d is not None and p is not None


def outcomes(worlds, evidence):
    return {answer for files, answer, _ in worlds
            if all(value is None or files[key] == value for key, value in evidence)}


def audit(cases):
    worlds = list(universe())
    require(len(cases) == len(worlds), "case coverage")
    totals = defaultdict(Counter)
    runs = 0
    for (value, probes, trials), (docs, winner, needs_loader) in zip(cases, worlds):
        require(value == winner[0], "runtime value")
        expected = {k: (91 if k == winner[1] else value) for k in ("green.json", "defaults.json")
                    if "limit" in docs[k]}
        require(probes == expected, "intervention")
        runs += 1 + len(expected)
        require(len(trials) == 4, "trial coverage")
        for idx, (answer, trace) in enumerate(trials):
            blocked, conditional = divmod(idx, 2)
            names = [k for k, _ in trace]
            require(len(set(names)) == len(names) and 0 < len(names) <= 4, "budget")
            for key, obj in trace:
                require(key in docs and obj == (None if blocked and key == "loader.py" else docs[key]), "receipt")
            possible = outcomes(worlds, trace)
            require(answer == (list(winner) if len(possible) == 1 else None), "unsupported conclusion")
            require((answer is None) == bool(blocked and needs_loader), "avoidable abstention")
            require(("loader.py" in names) == (needs_loader if conditional else True), "loader necessity")
            group = ("hidden" if blocked else "available") + ("/conditional" if conditional else "/eager")
            stats = totals[group]
            stats["abstain" if answer is None else "correct"] += 1
            stats["reads"] += len(trace)
            stats["loader_requests"] += names.count("loader.py")
            if answer is not None:
                minimum = next(size for size in range(len(trace)+1)
                               if any(len(outcomes(worlds, subset)) == 1
                                      for subset in itertools.combinations(trace, size)))
                stats["reads_beyond_smallest_supporting_subset"] += len(trace) - minimum
    return {"app_starts": runs, "counts": totals}


if __name__ == "__main__":
    report = json.loads(Path(sys.argv[1]).read_bytes())
    require(report["commit"] == sys.argv[2], "commit")
    cases = json.loads(zlib.decompress(base64.b64decode(report["cases"], validate=True)))
    summary = audit(cases)
    for kind in ("intervention", "unsupported conclusion"):
        bad = copy.deepcopy(cases)
        # Enabled, both definitions zero, first loader. Hidden loader leaves two possible sources.
        equal_values = bad[13]
        if kind == "intervention":
            equal_values[1]["defaults.json"] = 91
        else:
            equal_values[2][3][0] = [0, "defaults.json"]
        try:
            audit(bad)
        except ValueError as error:
            require(str(error) == kind, "mutation reason")
        else:
            raise ValueError("accepted altered receipt")
    print("AUDIT " + json.dumps(summary))
