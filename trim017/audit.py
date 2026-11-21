"""Independently grade receipts and match every prior answer to its case."""
from itertools import product
import json
from pathlib import Path
import sys


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def grade(receipts, history, commit):
    require(receipts[0] == "COMMIT " + commit, "tested source")
    require(history["tested_commit"] == "3fceb6a7a3ba0eae3c79ab19f333e2d8000541d1", "historical source")
    old = {}
    for line in history["records"][1:]:
        spec, output, tag, _, _, answer = json.loads(line[5:])
        names = ("theme.json", "session.json") if spec[0] == "mint" else ("defaults.json", "boot.json")
        old[tuple(spec)] = (output, dict(zip(("oracle-0", "oracle-1"), names))[tag], answer)
    fresh = set(product(("unicode", "blank", "twice", "two_files", "join", "upper"), (False, True)))
    require(len(old) == 28, "historical coverage")
    counts = dict(retained=0, recovered=0, old_wrong=0, new_correct=0, new_wrong=0,
                  new_abstain=0, mixed_abstain=0, upper_abstain=0)
    seen = set()
    for line in receipts[1:]:
        require(line.startswith("CASE "), "row framing")
        spec, output, observed, answer, probes = json.loads(line[5:])
        key = tuple(spec)
        require(key not in seen and key in old.keys() | fresh, "case identity")
        seen.add(key)
        require(observed["stdout"] == json.dumps(output) + "\n", "instrumentation changed output")
        require(len(observed["sinks"]) == 1, "sink count")
        source, value = observed["sinks"][0]
        require(value == output and answer == source, "answer unsupported by receipt")
        if key in old:
            expected, truth, previous = old[key]
            require(expected == output and probes is None and previous in (truth, None), "historical baseline")
            if answer == truth:
                counts["recovered" if previous is None else "retained"] += 1
            elif answer is not None:
                counts["old_wrong"] += 1
            continue
        style, reverse = spec
        first, second = ("right.json", "left.json") if reverse else ("left.json", "right.json")
        require(set(probes) == {first, second}, "intervention coverage")
        depends = {name for name, changed in probes.items() if changed != output}
        mixed = style in ("two_files", "join")
        require(depends == ({first, second} if mixed else {first}), "fixture intervention")
        ordinary = {"unicode": "cedar", "blank": "", "twice": "cedar", "two_files": "cedar",
                    "join": "cedar !", "upper": "CEDAR"}[style]
        require(output == ordinary, "fixture output")
        if answer is None:
            counts["new_abstain"] += 1
            counts["mixed_abstain"] += int(mixed)
            counts["upper_abstain"] += int(style == "upper")
        elif depends == {answer}:
            counts["new_correct"] += 1
        else:
            counts["new_wrong"] += 1
    require(seen == old.keys() | fresh, "incomplete records")
    target = counts == dict(retained=24, recovered=4, old_wrong=0, new_correct=6,
                            new_wrong=0, new_abstain=6, mixed_abstain=4, upper_abstain=2)
    return {"counts": counts, "target_met": target}


if __name__ == "__main__":
    lines = Path(sys.argv[1]).read_text().splitlines()
    history = json.loads(Path(sys.argv[2]).read_text())
    result = grade(lines, history, sys.argv[3])
    for mutation, reason in (("duplicate", "case identity"), ("missing", "incomplete records"),
                             ("sink", "answer unsupported by receipt")):
        edited = list(lines)
        if mutation == "duplicate":
            edited.append(edited[-1])
        elif mutation == "missing":
            edited.pop()
        else:
            row = json.loads(edited[-1][5:])
            row[3] = "fabricated.json"
            edited[-1] = "CASE " + json.dumps(row)
        try:
            grade(edited, history, sys.argv[3])
        except ValueError as exc:
            require(str(exc) == reason, "incorrect rejection")
        else:
            raise ValueError("accepted corrupted receipt")
    print("AUDIT", json.dumps(dict(result, corrupted_receipts_rejected=3)))
