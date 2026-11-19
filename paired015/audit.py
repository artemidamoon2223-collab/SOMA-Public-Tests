"""Verify a preserved receipt without importing the policy, app or engine."""
import argparse
import copy
import itertools
import json
from pathlib import Path

FILES = ["defaults.json", "boot.json"]


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def review(rows):
    keys = set(itertools.product(("amber", "teal"), ("literal", "computed"),
                                 (False, True), ("open", "no_probes")))
    pairs = {}
    scores = [dict(correct=0, wrong=0, abstain=0, checks=0, requested=0, contradicted_by_probe=0) for _ in range(2)]
    for spec, output, tagged, decisions in rows:
        key = tuple(spec)
        require(type(spec[2]) is bool and key in keys, "case membership")
        keys.remove(key)
        value, spelling, active, access = spec
        require(output == value and tagged == f"oracle-{int(active)}", "mechanical oracle")
        require(len(decisions) == 2, "decision count")
        names = FILES if spelling == "literal" else FILES[:1]
        for i, (trace, answer) in enumerate(decisions):
            require(trace and trace[0] == ["inspect", names], "first observation")
            target = names[-1]
            observable = access == "open"
            expected_probe = ("changed" if target == FILES[active] else "unchanged") if observable else "unavailable"
            requested = len(trace) == 2
            require(len(trace) in (1, 2) and (not requested or trace[1] ==
                    ["probe", target, expected_probe]), "probe receipt")
            require(requested == (i == 1 or spelling == "literal"), "frozen schedule")
            if requested and observable:
                # CI-014 retains its first conclusion when elimination leaves no alternatives.
                expected = target if expected_probe == "changed" or len(names) == 1 else names[0]
            else:
                expected = names[0] if len(names) == 1 else None
            require(answer == expected, "decision receipt")
            counts = scores[i]
            if requested and expected_probe == "unchanged" and answer == target:
                counts["contradicted_by_probe"] += 1
            counts["checks"] += len(trace)
            counts["requested"] += int(requested)
            category = "abstain" if answer is None else "correct" if answer == FILES[active] else "wrong"
            counts[category] += 1
        group = (value, spelling, access)
        pairs.setdefault(group, {})[active] = (output, decisions[0][0][0], len(decisions[0][0]), tagged)
    require(not keys, "incomplete matrix")
    premature = []
    for group, pair in sorted(pairs.items()):
        off, on = pair[False], pair[True]
        require(off[:2] == on[:2] and off[3] != on[3], "paired indistinguishability")
        if min(off[2], on[2]) < 2:
            premature.append(group)
    return {"pairs": len(pairs), "premature_stop_pairs": premature, "scores": scores,
            "claim_pass": not premature and scores[0]["wrong"] == 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    parser.add_argument("commit")
    args = parser.parse_args()
    lines = args.receipt.read_text().splitlines()
    require(lines[0] == "COMMIT " + args.commit, "source commit")
    require(all(line.startswith("CASE ") for line in lines[1:]), "record type")
    rows = [json.loads(line[5:]) for line in lines[1:]]
    summary = review(rows)
    for kind in ("incomplete matrix", "mechanical oracle", "probe receipt", "decision receipt"):
        modified = copy.deepcopy(rows)
        if kind == "incomplete matrix":
            modified.pop()
        elif kind == "mechanical oracle":
            modified[0][2] = "wrong"
        elif kind == "probe receipt":
            modified[0][3][0][0][1][2] = "unavailable"
        else:
            modified[0][3][0][1] = "unearned"
        try:
            review(modified)
        except ValueError as error:
            require(str(error) == kind, "unexpected control failure")
        else:
            raise ValueError("corrupted receipt accepted")
    print("AUDIT", json.dumps(dict(summary, rejected_corruptions=4), sort_keys=True))


if __name__ == "__main__":
    main()
