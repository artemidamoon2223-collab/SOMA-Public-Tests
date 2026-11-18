"""Recover possible conclusions from all worlds consistent with each file transcript."""
import base64
from collections import Counter, defaultdict
import itertools
import json
from pathlib import Path
import sys
import zlib

FILES = ["defaults.json", "launch.json", "blue.json", "green.json"]
NAMES = ["defaults_only", "fixed", "adaptive"]


def check(ok, message):
    if not ok:
        raise ValueError(message)


def worlds():
    for d, mode, b, g in itertools.product((0, 7), (None, "blue", "green"), (None, 0, 7), (None, 0, 7)):
        values = [d, mode, b, g]
        docs = [{"profile": v} if i == 1 else {} if v is None else {"limit": v}
                for i, v in enumerate(values)]
        winner = 0
        if mode:
            i = 2 if mode == "blue" else 3
            if values[i] is not None:
                winner = i
        yield dict(zip(FILES, docs)), (values[winner], FILES[winner])


def audit(cases):
    universe = list(worlds())
    check(len(cases) == len(universe), "coverage")
    counts = defaultdict(Counter)
    runs = 0
    for (docs, truth), (initial, perturb, schedules) in zip(universe, cases):
        check(initial == truth[0], "application value")
        expected = {k: 91 if k == truth[1] else initial for k, v in docs.items() if "limit" in v}
        check(perturb == expected, "causal intervention")
        runs += 1 + len(perturb)
        check(len(schedules) == 5, "delivery coverage")
        for blocked, trials in zip([None, *FILES], schedules):
            check(len(trials) == 3, "policy coverage")
            for name, (answer, trace) in zip(NAMES, trials):
                reads = [k for k, _ in trace]
                check(0 < len(reads) <= 3 and len(set(reads)) == len(reads), "read budget")
                for k, v in trace:
                    check(k in docs and v == (None if k == blocked else docs[k]), "read evidence")
                possible = {target for other, target in universe
                            if all(v is None or other[k] == v for k, v in trace)}
                if name != "defaults_only":
                    justified = list(next(iter(possible))) if len(possible) == 1 else None
                    check(answer == justified, "unsupported conclusion")
                result = ("abstain" if answer is None else "correct" if tuple(answer) == truth
                          else "wrong_source_only" if answer[0] == initial else "wrong_value")
                group = "all_available" if blocked is None else "one_unavailable"
                counts[group + "/" + name].update({result: 1, "reads": len(trace)})
    return {"application_runs": runs, "results": counts}


if __name__ == "__main__":
    report = json.loads(Path(sys.argv[1]).read_bytes())
    check(report["sha"] == sys.argv[2], "revision")
    cases = json.loads(zlib.decompress(base64.b64decode(report["cases"], validate=True)))
    summary = audit(cases)
    cases[0][1]["defaults.json"] = 0
    try:
        audit(cases)
    except ValueError as error:
        check(str(error) == "causal intervention", "mutation reason")
    else:
        raise ValueError("accepted corrupt intervention")
    print("AUDIT " + json.dumps(summary))
