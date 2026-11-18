"""Enumerate all complete worlds compatible with the received transcript."""
import base64
import collections
import json
from pathlib import Path
import sys
import zlib

NAMES = ["first_difference", "fixed_robust", "difference_robust"]


def require(condition, error):
    if not condition:
        raise ValueError(error)


def audit(report, sha):
    require(report["commit"] == sha, "revision")
    rows = zlib.decompress(base64.b64decode(report["traces"], validate=True)).decode().splitlines()
    require(len(rows) == 2560, "coverage")
    counters = {policy: collections.Counter() for policy in NAMES}
    for index, row in enumerate(rows):
        pair, case = divmod(index, 10)
        truth, fault = divmod(case, 5)
        models = divmod(pair, 16)
        actual = models[truth] ^ (0 if fault == 0 else 1 << (4 - fault))
        traces = row.split(",")
        require(len(traces) == 3, "strategies")
        for policy, trace in zip(NAMES, traces):
            possible = [(h, word) for h, model in enumerate(models) for word in range(16)
                        if (word ^ model).bit_count() <= int(policy != "first_difference")]
            events, answer = trace.split("=")
            require(len(events) in (0, 2, 4, 6), "budget")
            used = set()
            for pos in range(0, len(events), 2):
                channel, value = map(int, events[pos:pos+2])
                require(len({h for h, _ in possible}) == 2, "late query")
                order = sorted(set(range(4)) - used)
                if policy != "fixed_robust":
                    order.sort(key=lambda c: -((models[0] ^ models[1]) >> (3-c) & 1))
                require(channel == order[0] and value == (actual >> (3-channel) & 1), "observation")
                used.add(channel)
                possible = [(h, w) for h, w in possible if w >> (3-channel) & 1 == value]
            labels = {h for h, _ in possible}
            expected = str(next(iter(labels))) if len(labels) == 1 else "?"
            require(answer == expected, "verdict")
            require(len(labels) != 2 or len(used) == 3, "early abstention")
            metric = "abstain" if answer == "?" else "correct" if int(answer) == truth else "wrong"
            counters[policy][metric] += 1
            counters[policy]["queries"] += len(used)
            if policy != "first_difference":
                require(metric != "wrong", "unsafe decision")
    require(report["two_error_truth_zero"] == "0111=1", "boundary control")
    return counters


if __name__ == "__main__":
    doc = json.loads(Path(sys.argv[1]).read_bytes())
    counts = audit(doc, sys.argv[2])
    lines = zlib.decompress(base64.b64decode(doc["traces"])).decode().splitlines()
    for corrupt, reason in [(lines[:-1], "coverage"), ([lines[0].replace("=?", "=0", 1), *lines[1:]], "verdict")]:
        bad = dict(doc, traces=base64.b64encode(zlib.compress("\n".join(corrupt).encode())).decode())
        try:
            audit(bad, sys.argv[2])
        except ValueError as error:
            require(str(error) == reason, "wrong rejection")
        else:
            raise ValueError("false report accepted")
    print("AUDIT " + json.dumps(counts))
