"""Independent transcript oracle. Does not import the planner, domains or application runner."""
import base64
import copy
import hashlib
import itertools
import json
from pathlib import Path
import sys
import zlib


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def unpack(record):
    return json.loads(zlib.decompress(base64.b64decode(record["rows"], validate=True)))


def verify(rows, rules, transfer):
    files = ("routing.json", "events.json") if transfer else ("base.json", "layer.json")
    specs = itertools.product(("mail", "batch") if transfer else ("zero", "seven"), (False, True),
                              ("empty", "old", "mail", "batch", "other") if transfer else (None, "zero", "seven"),
                              ("open", "no_probes", "opaque") if transfer else ("open", "opaque"))
    scores = [dict(correct=0, wrong=0, abstain=0, checks=0) for _ in rules]
    strata = [{} for _ in rules]
    require(len(rows) == (60 if transfer else 24), "coverage")
    for spec, row in zip(specs, rows):
        base, active, value, access = spec
        present = value not in ("old", "empty", None)
        winner = int(active and present)
        initial = value if winner else base
        input_spec, observed, tag, arms = row
        require(list(spec) == input_spec and observed == initial and tag == "oracle-" + str(winner), "oracle")
        require(len(arms) == len(rules), "arms")
        for i, ((first, guard), (trace, answer)) in enumerate(zip(rules, arms)):
            require(len(trace) in (1, 2), "budget")
            candidates = set([0, 1, 2])  # 2 denotes an as-yet unnamed outside source
            if initial != base:
                candidates.remove(0)
            discovered = False
            for n, action in enumerate(trace):
                kind = first if n == 0 else ("inspect" if first == "probe" else "probe")
                require(action[0] == kind, "action order")
                if kind == "inspect":
                    deps = list(files[:1+int(active)]) if access != "opaque" else None
                    require(action == [kind, deps], "code evidence")
                    if deps:
                        candidates.intersection_update(range(len(deps)))
                        discovered = True
                else:
                    target = int(n == 1 and discovered and active)
                    response = ("unavailable" if access != "open" else "absent" if target and not present
                                else "changed" if target == winner else "unchanged")
                    require(action == [kind, files[target], response], "intervention")
                    if response == "changed":
                        candidates.intersection_update([target])
                    elif response in ("absent", "unchanged"):
                        candidates.discard(target)
                supported = None
                if len(candidates) == 1:
                    only = next(iter(candidates))
                    if only == 0 or (only == 1 and discovered):
                        supported = files[only]
                if n == 0:
                    second = (guard == "always" or (guard == "different" and base != initial)
                              or (guard == "unresolved" and supported is None))
                    require(len(trace) == 1 + int(second), "trigger")
            require(answer == supported, "unsupported answer")
            status = "abstain" if answer is None else "correct" if answer == files[winner] else "wrong"
            scores[i][status] += 1
            scores[i]["checks"] += len(trace)
            group = strata[i].setdefault(access, dict(correct=0, wrong=0, abstain=0, checks=0))
            group[status] += 1
            group["checks"] += len(trace)
    return scores, strata


def validate_training(record, sha):
    freeze = record["freeze"]
    rules = list(map(list, itertools.product(("inspect", "probe"), ("always", "unresolved", "different", "never"))))
    rows = unpack(record)
    require(freeze["sha"] == sha and freeze["rules"] == rules and freeze["train_hash"] == digest(rows), "provenance")
    scores, _ = verify(rows, rules, False)
    require(scores == freeze["scores"] and record["hash"] == digest(freeze), "selection evidence")
    eligible = [i for i,s in enumerate(scores) if s["wrong"] == 0]
    chosen = min(eligible, key=lambda i: (-scores[i]["correct"], scores[i]["checks"], i))
    require(rules[chosen] == freeze["selected"], "selection")
    return freeze


if __name__ == "__main__":
    training = json.loads(Path(sys.argv[1]).read_bytes())
    frozen = validate_training(training, sys.argv[2])
    if len(sys.argv) == 3:
        print(training["hash"])
    else:
        transfer = json.loads(Path(sys.argv[3]).read_bytes())
        require(transfer["sha"] == sys.argv[2] and transfer["freeze_hash"] == training["hash"], "transfer linkage")
        rows = unpack(transfer)
        rules = [frozen["selected"], ("inspect", "always")]
        scores, strata = verify(rows, rules, True)
        for label in ("oracle", "unsupported answer"):
            broken = copy.deepcopy(rows)
            if label == "oracle":
                broken[0][2] = "forged"
            else:
                broken[0][3][0][1] = "forged"
            try:
                verify(broken, rules, True)
            except ValueError as exc:
                require(str(exc) == label, "mutation reason")
            else:
                raise ValueError("corruption accepted")
        selected, baseline = scores
        improves = (selected["wrong"] == 0 and selected["correct"] >= baseline["correct"]
                    and selected["checks"] < baseline["checks"])
        print("AUDIT " + json.dumps(dict(scores=scores, strata=strata, improvement=improves)))
