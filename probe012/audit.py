"""Reconstruct both possible worlds and score the original value/source pair."""
import base64
from collections import Counter
import copy
import itertools
import json
from pathlib import Path
import sys
import zlib

NAMES = ("always_blue", "conditional_blue", "conditional_defaults", "select")
TARGETS = ("blue", "green", "defaults")
MARKERS = {"defaults": 84, "blue": 85, "green": 86, None: None}


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def outcome(default, profiles, active, fill):
    result = default, ("defaults" if default is not None else None)
    selected = profiles.get(active)
    if selected is not None and (default is None or not fill):
        result = selected, active
    return result


def audit(rows):
    cases = list(itertools.product(range(2), (None, "blue", "green"), *((None, 0, 7),)*3))
    check(len(rows) == len(cases), "coverage")
    totals = {name: Counter() for name in NAMES}
    ambiguous = 0
    for (mode, active, d, b, g), (baseline, tagged, trials) in zip(cases, rows):
        profiles = {"blue": b, "green": g}
        originals = [outcome(d, profiles, active, m) for m in range(2)]
        check(baseline == originals[mode][0] and tagged == MARKERS[originals[mode][1]], "ground truth")
        modes = [m for m in range(2) if originals[m][0] == baseline]
        unclear = len({originals[m] for m in modes}) > 1
        ambiguous += unclear
        check(len(trials) == len(NAMES), "arms")
        for name, (receipts, answer) in zip(NAMES, trials):
            check(len(receipts) == int(unclear or name == "always_blue"), "budget or trigger")
            survivors = modes
            if receipts:
                target, observed = receipts[0]
                projections = {}
                for action in TARGETS:
                    dd = 91 if action == "defaults" else d
                    pp = dict(profiles)
                    if action in profiles:
                        pp[action] = 91
                    projections[action] = [outcome(dd, pp, active, m)[0] for m in range(2)]
                if name == "select":
                    choice = max(TARGETS, key=lambda a: len({projections[a][m] for m in modes}))
                else:
                    choice = "defaults" if name == "conditional_defaults" else "blue"
                check(target == choice and observed == projections[target][mode], "intervention")
                survivors = [m for m in modes if projections[target][m] == observed]
                totals[name]["probes"] += 1
            pairs = {originals[m] for m in survivors}
            check(answer == (list(originals[mode]) if len(pairs) == 1 else None), "unsupported answer")
            totals[name]["abstain" if answer is None else "correct"] += 1
            if unclear and answer is not None:
                totals[name]["ambiguous_resolved"] += 1
    return {"cases": len(cases), "ambiguous": ambiguous, "arms": totals,
            "app_starts": 2 * len(cases) + sum(c["probes"] for c in totals.values())}


if __name__ == "__main__":
    report = json.loads(Path(sys.argv[1]).read_bytes())
    check(report["sha"] == sys.argv[2], "commit")
    data = json.loads(zlib.decompress(base64.b64decode(report["rows"], validate=True)))
    stats = audit(data)
    for reason in ("ground truth", "intervention", "unsupported answer"):
        altered = copy.deepcopy(data)
        if reason == "ground truth":
            altered[0][1] = 86
        elif reason == "intervention":
            altered[0][2][0][0][0][1] = 999
        else:
            altered[0][2][0][1] = [7, "green"]
        try:
            audit(altered)
        except ValueError as error:
            check(str(error) == reason, "mutation reason")
        else:
            raise ValueError("accepted corrupt receipt")
    print("AUDIT " + json.dumps(stats))
