"""Independent oracle using integer truth tables and full enumeration of leaf sizes."""
import base64
from collections import Counter
import itertools
import json
import sys
from pathlib import Path
import zlib


def bit(word, channel):
    return (word >> (2 - channel)) & 1


def rank(menu, plan):
    first, zero, one = plan
    signatures = [(bit(w, first), bit(w, one if bit(w, first) else zero)) for w in menu]
    hits = sum(signatures.count(signature) == 1 for signature in signatures)
    first_bits = [signature[0] for signature in signatures]
    cost = 4 + sum(first_bits.count(b) > 1 for b in first_bits)
    return -hits, cost, plan


def audit(rows):
    if len(rows) != 560:
        raise ValueError("coverage")
    totals = [Counter(), Counter()]
    differences = Counter()
    cursor = 0
    for menu in itertools.combinations(range(8), 4):
        scores = [0, 0]
        allowed = [p for p in itertools.product(range(3), repeat=3) if p[0] not in p[1:]]
        plans = [min((rank(menu, p) for p in allowed if adaptive or p[1] == p[2]))[2]
                 for adaptive in (False, True)]
        for label, word in enumerate(menu):
            for strategy, plan in enumerate(plans):
                actual_plan, trace, conclusion = rows[cursor]
                cursor += 1
                if tuple(actual_plan) != plan:
                    raise ValueError("plan")
                first = bit(word, plan[0])
                expected = [[plan[0], first]]
                if sum(bit(w, plan[0]) == first for w in menu) > 1:
                    second = plan[first + 1]
                    expected.append([second, bit(word, second)])
                if trace != expected:
                    raise ValueError("transcript")
                matches = [w for w in menu if all(bit(w, c) == val for c, val in trace)]
                verdict = label if len(matches) == 1 else None
                if conclusion != verdict:
                    raise ValueError("verdict")
                totals[strategy]["correct" if conclusion is not None else "abstain"] += 1
                totals[strategy]["queries"] += len(trace)
                scores[strategy] += conclusion is not None
        differences[scores[1] - scores[0]] += 1
    return dict(static=totals[0], adaptive=totals[1], menu_gain=differences)


if __name__ == "__main__":
    doc = json.loads(Path(sys.argv[1]).read_bytes())
    if doc["commit"] != sys.argv[2]:
        raise ValueError("commit")
    rows = json.loads(zlib.decompress(base64.b64decode(doc["traces"], validate=True)))
    totals = audit(rows)
    for bad, reason in [(rows[:-1], "coverage"), ([[rows[0][0], [], rows[0][2]], *rows[1:]], "transcript")]:
        try:
            audit(bad)
        except ValueError as error:
            if str(error) != reason:
                raise
        else:
            raise ValueError("corrupt report accepted")
    print("AUDIT " + json.dumps(totals))
