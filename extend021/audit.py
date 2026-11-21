"""Independent receipt verifier. Does not import the decision rule or the loader."""
from collections import Counter
from itertools import product
import json
from pathlib import Path
import sys


def check(test, reason):
    if not test:
        raise ValueError(reason)


def expected(files, observed):
    positive = sorted(f for f, changed in observed.items() if changed)
    negative = sorted(f for f, changed in observed.items() if not changed)
    unknown = sorted(set(files) - observed.keys())
    return dict(present=positive, absent=negative, unknown=unknown,
                exact=positive if len(observed) == len(files) else None)


def audit(lines, history, sha):
    check(lines[0] == "COMMIT " + sha, "commit")
    check(history["tested_commit"] == "93cfe14237f1031f194005ff5559ba45943ac236", "parent")
    parent = {tuple(r[0]): r for r in (json.loads(l[5:]) for l in history["records"][1:])}
    todo = set(product(("two_names", "nonempty"), ("open", "one"), range(8)))
    todo.update(("control", i) for i in range(4))
    check(set(parent) == todo, "history membership")
    scores = {}
    for line in lines[1:]:
        check(line.startswith("CASE "), "framing")
        key, initial, target, results = json.loads(line[5:])
        k = tuple(key)
        check(k in todo, "case identity")
        todo.remove(k)
        _, baseline, _, files, trace, previous, oracle = parent[k]
        observed = {f: value != baseline for f, value in trace}
        truth = {f for f in files if oracle[f] != baseline}
        check(all((f in truth) == b for f, b in observed.items()), "history oracle")
        check(initial == expected(files, observed) and initial["present"] == previous["confirmed"]
              and initial["unknown"] == previous["untested"], "initial report")
        check(target == min(initial["unknown"], default=None), "request")
        group = "control" if key[0] == "control" else key[1]
        counts = scores.setdefault(group, Counter())
        counts["cases"] += 1
        counts["requests"] += int(target is not None)
        check(set(results) == {"allow", "deny"}, "branches")
        for mode, (log, final) in results.items():
            allowed = mode == "allow" and target is not None
            expected_log = [[target, "EXTENSION" if target in truth else baseline]] if allowed else []
            check(log == expected_log, "worker log")
            after = observed.copy()
            if allowed:
                after[target] = target in truth
            check(final == expected(files, after), "final report")
            if final["exact"] is not None:
                check(set(final["exact"]) == truth, "false exact")
            counts[mode + "_edits"] += len(log)
            counts[mode + "_exact"] += int(final["exact"] is not None)
            counts[mode + "_partial"] += int(final["exact"] is None)
    check(not todo, "missing cases")
    return scores


if __name__ == "__main__":
    lines = Path(sys.argv[1]).read_text().splitlines()
    history = json.loads(Path(sys.argv[2]).read_bytes())
    result = audit(lines, history, sys.argv[3])
    for reason in ("request", "worker log", "final report", "missing cases"):
        altered = lines.copy()
        if reason == "missing cases":
            altered.pop()
        else:
            row = json.loads(altered[1][5:])
            if reason == "request":
                row[2] = "invented.json"
            elif reason == "worker log":
                row[3]["deny"][0].append([row[2], "EXTENSION"])
            else:
                row[3]["deny"][1]["exact"] = []
            altered[1] = "CASE " + json.dumps(row)
        try:
            audit(altered, history, sys.argv[3])
        except ValueError as exc:
            check(str(exc) == reason, "wrong rejection")
        else:
            raise ValueError("corrupt evidence accepted")
    print("AUDIT", json.dumps(dict(scores=result, corruptions_rejected=4), sort_keys=True))
