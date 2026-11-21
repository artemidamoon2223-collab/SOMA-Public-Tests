"""Score transitions and demand an executed, different-truth twin for each abstention."""
from collections import Counter
from itertools import combinations, product
import json
from pathlib import Path
import sys


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def grade(lines, parent, sha):
    check(parent["tested_commit"] == "71e1f9df30d8cb085d08779fc570852211e525bf", "parent")
    check(lines[0] == "COMMIT " + sha, "commit")
    history = {tuple(r[0]): r for r in (json.loads(s[5:]) for s in parent["records"][1:])}
    expected = set(product(("two_names", "nonempty"), ("open", "one"), range(8)))
    check(history.keys() == expected, "parent cohort")
    expected.update(("control", i) for i in range(4))
    groups, transitions, challenges = {}, {}, Counter()
    paired = {}
    for line in lines[1:]:
        check(line.startswith("CASE "), "framing")
        key, out, witness, files, trace, decision, oracle = json.loads(line[5:])
        k = tuple(key)
        check(k in expected, "case identity")
        expected.remove(k)
        old = history.get(k)
        control = old is None
        check(files == (["a.json", "b.json"] if control else ["a.json", "b.json", "c.json"]), "inventory")
        check(out == "BASE" and witness == {"stdout": '"BASE"\n', "sinks": [[None, out]]}, "lost label")
        subsets = [list(s) for n in range(len(files)+1) for s in combinations(files,n)]
        truth = subsets[key[-1]]
        check(set(oracle) == set(files) and all(oracle[f] == ("ORACLE" if f in truth else out) for f in files), "oracle")
        if control:
            catalogue = [[files[0]], [files[1]]]
            prefix = [[files[0], "PLANNER" if files[0] in truth else out]]
            proposal = [files[0] if files[0] in truth else files[1]]
        else:
            check([out, witness, oracle] == [old[1], old[2], old[6]], "fixture drift")
            prefix, proposal = old[3:5]
            catalogue = [["a.json"], ["b.json"], files[:2]] if key[0] == "two_names" else subsets[1:]
        check(trace[:len(prefix)] == prefix and decision["provisional"] == proposal, "historical decision")
        allowed = files if control or key[1] == "open" else files[:1]
        names = [f for f, _ in trace]
        check(len(names) == len(set(names)) <= 2 and set(names) <= set(allowed), "budget")
        check(all(v == ("PLANNER" if f in truth else out) for f, v in trace), "probe")
        spare = set(allowed) - {n for n, _ in prefix}
        challenge = None
        if proposal is not None and spare and len(prefix) < 2:
            listed = set().union(*catalogue)
            name = min(spare, key=lambda f: (f in listed, f not in proposal, f))
            check(names[len(prefix):] == [name], "challenge target")
            challenge = [name, "consistent" if (name in truth) == (name in proposal) else "refuted"]
        else:
            check(len(prefix) == len(trace), "unexpected probe")
        check(decision["challenge"] == challenge, "challenge outcome")
        positive = sorted(f for f, v in trace if v != out)
        missing = sorted(set(files) - set(names))
        check(decision["confirmed"] == positive and decision["untested"] == missing, "partial evidence")
        check(decision["exact"] == (None if missing else positive), "exact answer")
        def status(answer):
            return "abstain" if answer is None else "correct" if answer == truth else "wrong"
        after = status(decision["exact"])
        group = "controls" if control else "historical"
        groups.setdefault(group, Counter())[after] += 1
        if not control:
            before = status(proposal)
            transitions.setdefault(before, Counter())[after] += 1
            event = challenge[1] if challenge else "no_challenge"
            challenges[(before, event)] += 1
            sig = (key[0], key[1], json.dumps(trace))
            paired.setdefault(sig, []).append((truth, after))
    check(not expected, "coverage")
    twins = 0
    for matches in paired.values():
        for truth, after in matches:
            if after == "abstain":
                check(any(other != truth for other, _ in matches), "missing observed twin")
                twins += 1
    return dict(groups=groups, transitions=transitions, challenges={a+"/"+b:v for (a,b),v in challenges.items()},
                abstentions_with_twin=twins)


if __name__ == "__main__":
    lines = Path(sys.argv[1]).read_text().splitlines()
    parent = json.loads(Path(sys.argv[2]).read_text())
    result = grade(lines,parent,sys.argv[3])
    for reason in ("case identity", "coverage", "exact answer"):
        bad = lines.copy()
        if reason == "case identity":
            bad.append(lines[1])
        elif reason == "coverage":
            bad.pop()
        else:
            row = json.loads(bad[1][5:])
            row[5]["exact"] = ["imaginary.json"]
            bad[1] = "CASE " + json.dumps(row)
        try:
            grade(bad,parent,sys.argv[3])
        except ValueError as err:
            check(str(err) == reason, "rejection reason")
        else:
            raise ValueError("accepted invalid evidence")
    print("AUDIT", json.dumps(dict(result, corruptions_rejected=3), sort_keys=True))
