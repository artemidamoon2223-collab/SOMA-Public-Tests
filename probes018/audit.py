"""Audit evidence without importing either planner or executing the fixture."""
import itertools
import json
from pathlib import Path
import sys


def require(test, reason):
    if not test:
        raise ValueError(reason)


def compatible(family, trace, output):
    return [h for h in family if all((f in h) == (v != output) for f, v in trace)]


def best_fixed(family, allowed):
    def rank(order):
        solved = cost = 0
        for truth in family:
            for used in range(len(order) + 1):
                same = [h for h in family if all((n in truth) == (n in h) for n in order[:used])]
                if len(same) == 1:
                    solved += 1
                    break
            cost += used
        return -solved, cost, order
    return min(itertools.permutations(allowed, min(2, len(allowed))), key=rank)


def audit(lines, prior, sha):
    require(prior["tested_commit"] == "b51395b46370ede5fce5152ebf22dd8f61655a5e", "parent binding")
    require(lines[0] == "COMMIT " + sha, "commit binding")
    old = {}
    for line in prior["records"][1:]:
        spec, out, witness, answer, probes = json.loads(line[5:])
        if answer is None:
            old[tuple(spec)] = (out, witness, {f for f, v in probes.items() if v != out})
    require(len(old) == 6, "old cohort")
    todo = {("old", *key) for key in old}
    todo.update(("new", shift, style, i) for shift in (0, 2)
                for style in ("fork", "early", "restricted", "denied")
                for i in range(3 if style == "early" else 4))
    metrics = {}
    forks = {}
    for line in lines[1:]:
        require(line.startswith("CASE "), "record type")
        key, output, witness, names, family, allowed, records, oracle = json.loads(line[5:])
        require(tuple(key) in todo, "case membership")
        todo.remove(tuple(key))
        require(witness == {"stdout": json.dumps(output) + "\n", "sinks": [[None, output]]}, "loss trigger")
        require(set(oracle) == set(names) and len(records) == 2, "evidence coverage")
        truth = {f for f, v in oracle.items() if v != output}
        if key[0] == "old":
            group = "prior"
            require((output, witness, truth) == old[tuple(key[1:])], "historical case")
            require(names == allowed == ["left.json", "right.json"] and family ==
                    [[], [names[0]], [names[1]], names], "prior contract")
        else:
            _, shift, group, variant = key
            labels = ["ash.json", "bay.json", "elm.json", "oak.json"]
            require(names == labels[shift:] + labels[:shift] and output == "XX", "new fixture")
            a, b, c, d = names
            options = [[a], [a, b], [c], [d]]
            require(family == (options[:3] if group == "early" else options), "declared family")
            require(allowed == ([] if group == "denied" else [a] if group == "restricted" else names), "access")
            require(truth == set(family[variant]), "ground truth")
        for mode, (trace, answer) in zip(("fixed", "adaptive"), records):
            seen = set()
            order = best_fixed(family, allowed)
            require(len(trace) <= 2, "budget")
            for i, (name, value) in enumerate(trace):
                remaining = compatible(family, trace[:i], output)
                require(name in allowed and name not in seen and len(remaining) > 1, "probe scope")
                def rank(f):
                    signatures = [f in h for h in remaining]
                    return max(signatures.count(False), signatures.count(True)), f
                planned = order[i] if mode == "fixed" else min(set(allowed) - seen, key=rank)
                require(name == planned, "probe choice")
                require((value != output) == (name in truth), "probe response")
                seen.add(name)
            remaining = compatible(family, trace, output)
            require(answer == (sorted(remaining[0]) if len(remaining) == 1 else None), "unearned answer")
            if len(remaining) > 1 and len(trace) < 2:
                useful = [f for f in set(allowed) - seen if 0 < sum(f in h for h in remaining) < len(remaining)]
                require(not useful, "unjustified stop")
            bucket = metrics.setdefault(group, {}).setdefault(mode, dict(correct=0, wrong=0, abstain=0,
                                        probes=0, solved_on_first=0, solved_on_second=0))
            bucket["probes"] += len(trace)
            if answer is None:
                bucket["abstain"] += 1
            elif set(answer) != truth:
                bucket["wrong"] += 1
            else:
                bucket["correct"] += 1
                bucket["solved_on_first" if len(trace) == 1 else "solved_on_second"] += 1
            if group == "fork" and mode == "adaptive":
                require(len(trace) == 2, "fork trace")
                first, second = trace
                forks.setdefault((shift, first[0], first[1] != output), set()).add(second[0])
    require(not todo, "missing cases")
    require(len(forks) == 4 and all(len(s) == 1 for s in forks.values()), "fork coverage")
    branching = all(len(set.union(*(s for (rot, _, _), s in forks.items() if rot == shift))) == 2 for shift in (0, 2))
    passed = (branching and metrics["prior"]["adaptive"]["correct"] == 6
              and metrics["fork"]["adaptive"]["correct"] > metrics["fork"]["fixed"]["correct"]
              and metrics["early"]["adaptive"]["solved_on_first"] > 0
              and all(metrics[s]["adaptive"]["correct"] == 0 for s in ("restricted", "denied"))
              and all(m["wrong"] == 0 for values in metrics.values() for m in values.values()))
    return dict(metrics=metrics, branching_in_both_rotations=branching, target_met=passed)


if __name__ == "__main__":
    lines = Path(sys.argv[1]).read_text().splitlines()
    prior = json.loads(Path(sys.argv[2]).read_text())
    result = audit(lines, prior, sys.argv[3])
    for kind in ("case membership", "missing cases", "unearned answer"):
        corrupt = lines.copy()
        if kind == "case membership":
            corrupt.append(lines[-1])
        elif kind == "missing cases":
            corrupt.pop()
        else:
            row = json.loads(corrupt[-1][5:])
            row[6][1][1] = ["invented.json"]
            corrupt[-1] = "CASE " + json.dumps(row)
        try:
            audit(corrupt, prior, sys.argv[3])
        except ValueError as error:
            require(str(error) == kind, "wrong rejection reason")
        else:
            raise ValueError("accepted corrupt evidence")
    print("AUDIT", json.dumps(dict(result, corrupt_receipts_rejected=3)))
