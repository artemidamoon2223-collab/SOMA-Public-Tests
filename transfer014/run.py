import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import digest, pack, run_case
from policy import RULES


def evaluate(domain, rules):
    with tempfile.TemporaryDirectory() as tmp:
        return [run_case(Path(tmp), domain, spec, rules) for spec in domain.cases()]


def score(rows, files, index):
    counts = dict(wrong=0, correct=0, abstain=0, checks=0)
    for _, _, tag, arms in rows:
        trace, answer = arms[index]
        winner = files[("oracle-0", "oracle-1").index(tag)]
        counts["abstain" if answer is None else "correct" if answer == winner else "wrong"] += 1
        counts["checks"] += len(trace)
    return counts


def rank(counts, i):
    return (bool(counts["wrong"]), -counts["correct"], counts["checks"], i)


phase, filename = sys.argv[1:]
path = Path(filename)
sha = os.environ["SOURCE_SHA"]
if phase == "train":
    import train_domain as domain
    rows = evaluate(domain, RULES)
    scores = [score(rows, domain.FILES, i) for i in range(len(RULES))]
    index = min(range(len(RULES)), key=lambda i: rank(scores[i], i))
    if scores[index]["wrong"]:
        raise ValueError("no eligible candidate")
    freeze = dict(sha=sha, rules=RULES, scores=scores, selected=RULES[index], train_hash=digest(rows))
    with path.open("x") as f:
        json.dump(freeze, f)
    print("FREEZE", json.dumps(dict(freeze=freeze, hash=digest(freeze), rows=pack(rows))))
elif phase == "transfer":
    freeze = json.loads(path.read_bytes())
    if digest(freeze) != os.environ["FREEZE_HASH"] or freeze["sha"] != sha:
        raise ValueError("freeze changed")
    import dispatch_domain as domain
    rules = [freeze["selected"], ("inspect", "always")]
    rows = evaluate(domain, rules)
    print("TRANSFER", json.dumps(dict(sha=sha, freeze_hash=digest(freeze), rows=pack(rows))))
else:
    raise ValueError("unknown phase")
