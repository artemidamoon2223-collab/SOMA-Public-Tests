"""Recompute ground truth, compatibility, and matched observational twins."""
import itertools
import json
from pathlib import Path
import sys

FILES = ("a.json", "b.json", "c.json")
ALL = [s for width in range(4) for s in itertools.combinations(FILES, width)]


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def audit(lines, sha):
    require(lines[0] == "COMMIT " + sha, "commit")
    expected = set(itertools.product(("two_names", "nonempty"), ("open", "one"), range(8)))
    totals, pairs, recorded = {}, [], {}
    control = dict(contradicted=0, compatible=0)
    for line in lines[1:]:
        require(line.startswith("CASE "), "framing")
        key, baseline, observed, trace, answer, challenge, oracle = json.loads(line[5:])
        label, access, index = key
        require(tuple(key) in expected, "case identity")
        expected.remove(tuple(key))
        family = [ALL[i] for i in (1, 2, 4)] if label == "two_names" else ALL[1:]
        require(baseline == "BASE" and observed == {"stdout": '"BASE"\n', "sinks": [[None, "BASE"]]}, "trigger")
        require(oracle == {f: "ORACLE" if f in ALL[index] else baseline for f in FILES}, "oracle")
        truth = tuple(f for f in FILES if oracle[f] != baseline)
        scope = set(FILES if access == "open" else FILES[:1])
        remaining = family.copy()
        require(len(trace) <= 2, "budget")
        for f, v in trace:
            require(f in scope and len(remaining) > 1, "scope")
            def rank(n):
                yes = sum(n in s for s in remaining)
                return max(yes, len(remaining) - yes), n
            require(f == min(scope, key=rank) and rank(f)[0] < len(remaining), "choice")
            scope.remove(f)
            require(v == ("PLANNER" if f in truth else baseline), "probe")
            remaining = [s for s in remaining if (f in s) == (v != baseline)]
        if len(trace) < 2 and len(remaining) > 1:
            require(not any(0 < sum(f in s for s in remaining) < len(remaining) for f in scope), "stop")
        require(answer == (list(remaining[0]) if len(remaining) == 1 else None), "answer")
        group = "listed" if truth in family else "omitted"
        b = totals.setdefault((group, access), dict(correct=0, wrong=0, abstain=0, contradiction=0))
        b["contradiction"] += int(not remaining)
        b["abstain" if answer is None else "correct" if tuple(answer) == truth else "wrong"] += 1
        recorded[(label, access, truth)] = (trace, answer)
        if answer is not None and tuple(answer) != truth:
            pairs.append(((label, access, truth), (label, access, tuple(answer))))
        if label == "two_names" and access == "open":
            require(challenge == ["c.json", "CONTROL" if "c.json" in truth else baseline], "challenge")
            compatible = any(("c.json" in h) == (challenge[1] != baseline) for h in family)
            control["compatible" if compatible else "contradicted"] += 1
        else:
            require(challenge is None, "extra challenge")
    require(not expected, "missing cases")
    for mistaken, twin in pairs:
        require(recorded[mistaken] == recorded[twin], "observational twin")
    return {"scores": {"/".join(k): v for k, v in totals.items()}, "wrong_with_exact_twin": len(pairs),
            "external_control": control, "zero_false_answers": not pairs}


if __name__ == "__main__":
    rows = Path(sys.argv[1]).read_text().splitlines()
    result = audit(rows, sys.argv[2])
    for reason in ("case identity", "missing cases", "oracle"):
        bad = rows.copy()
        if reason == "case identity":
            bad.append(rows[-1])
        elif reason == "missing cases":
            bad.pop()
        else:
            row = json.loads(bad[1][5:])
            row[-1]["a.json"] = "BAD"
            bad[1] = "CASE " + json.dumps(row)
        try:
            audit(bad, sys.argv[2])
        except ValueError as error:
            require(str(error) == reason, "rejection reason")
        else:
            raise ValueError("corruption accepted")
    print("AUDIT", json.dumps(dict(result, rejected_corruptions=3)))
