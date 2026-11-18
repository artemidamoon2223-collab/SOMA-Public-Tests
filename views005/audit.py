"""Independent small-model oracle and transcript checks. No protocol imports."""
import base64
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import zlib

ROOT = Path(__file__).resolve().parent.parent
FILES = {".github/workflows/soma-views-005.yml", "views005/README.md", "views005/witness.py",
         "views005/experiment.py", "views005/audit.py"}
# label, recipient, round, local view, other fixture's actual view, received sender/view, verdict
TRACE = [
    ("honest-world-hidden", "left", 1, "ABA", "ABA", None, "UNKNOWN"),
    ("forked-world-hidden", "left", 1, "ABA", "ABB", None, "UNKNOWN"),
    ("other-observer-hidden", "right", 1, "ABB", "ABA", None, "UNKNOWN"),
    ("reflection", "right", 1, "ABB", "ABA", ("right", 1, "ABB"), "INVALID"),
    ("altered", "right", 1, "ABB", "ABA", ("left", 1, "AAA"), "INVALID"),
    ("delivered-right", "right", 1, "ABB", "ABA", ("left", 1, "ABA"), "FORK"),
    ("still-hidden-left", "left", 1, "ABA", "ABB", None, "UNKNOWN"),
    ("delivered-left", "left", 1, "ABA", "ABB", ("right", 1, "ABB"), "FORK"),
    ("restart-left-withheld", "left", 2, "A", "A", None, "KNOWN_FORK"),
    ("restart-right-withheld", "right", 2, "A", "A", None, "KNOWN_FORK"),
    ("old-round", "left", 2, "AB", None, ("right", 1, "ABB"), "STALE"),
    ("prefix", "left", 2, "AB", "ABA", ("right", 2, "ABA"), "PREFIX"),
    ("equal", "left", 2, "AB", "AB", ("right", 2, "AB"), "EQUAL"),
]


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def matrix_oracle(encoded):
    compressed = base64.b64decode(encoded, validate=True)
    decoder = zlib.decompressobj()
    raw = decoder.decompress(compressed, 65536)
    require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, "matrix encoding")
    lines = iter(raw.decode().splitlines())
    words = ["", "A", "B", "AA", "AB", "BA", "BB",
             "AAA", "AAB", "ABA", "ABB", "BAA", "BAB", "BBA", "BBB"]
    counts = Counter()
    for first in words:
        for second in words:
            pos = 0
            if first == second:
                seen = "EQUAL"
            elif first.startswith(second) or second.startswith(first):
                seen = "PREFIX"
            else:
                seen = "FORK"
                pos = next(n for n in range(1, min(len(first), len(second)) + 1)
                           if first[:n] != second[:n])
            delivered = (seen, str(pos))
            absent = ("UNKNOWN", "0")
            for mask, (left, right) in enumerate([(absent, absent), (delivered, absent),
                                                  (absent, delivered), (delivered, delivered)]):
                expected = [first or "-", second or "-", str(mask), *left, *right]
                require(next(lines, "").split("\t") == expected, "matrix decision")
                counts.update([left[0], right[0]])
    require(next(lines, None) is None, "extra matrix row")
    return dict(counts)


def audit(doc, sha):
    require(doc["schema"] == 1 and doc["commit"] == sha and re.fullmatch("[0-9a-f]{40}", sha), "commit")
    require(doc["independence"] == "NOT_VERIFIED", "trust")
    require(doc["files"] == {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in FILES}, "hashes")
    counts = matrix_oracle(doc["matrix"])
    trace = doc["trace"]
    require(len(trace) == len(TRACE), "trace count")
    proofs = {}
    for row, (label, role, turn, own, other, peer, verdict) in zip(trace, TRACE):
        opposite = "right" if role == "left" else "left"
        require((row["label"], row["role"], row["turn"]) == (label, role, turn), "trace identity")
        require(row["local"] == ["tiles-v1", role, turn, own], "local view")
        remote = ["tiles-v1", opposite, turn, other] if other is not None else None
        require(row["remote_fixture"] == remote, "hidden fixture")
        require(row["peer"] == (["tiles-v1", *peer] if peer else None), "disclosed input")
        has_fork = verdict in {"FORK", "KNOWN_FORK"}
        require(row["verdict"] == [verdict, 3 if has_fork else 0], "trace decision")
        require(row["exit"] == (3 if verdict in {"STALE", "INVALID"} else 0) and row["stderr"] == "", "exit")
        require(re.fullmatch("[0-9a-f]{64}", row["input_digest"]), "input hash")
        if verdict == "FORK":
            proof = row["proof"]
            require(proof[:3] == [turn, row["local"], row["peer"]] and re.fullmatch("[0-9a-f]{64}", proof[3]),
                    "captured evidence")
            proofs[role] = proof
        elif verdict == "KNOWN_FORK":
            require(row["proof"] == proofs[role], "retained evidence")
        else:
            require(row["proof"] is None, "unexpected evidence")
    require(trace[0]["input_digest"] == trace[1]["input_digest"], "indistinguishability")
    return counts


def negative_controls(doc, sha):
    def matrix_flip(d):
        raw = zlib.decompress(base64.b64decode(d["matrix"])).replace(b"UNKNOWN", b"EQUAL", 1)
        d["matrix"] = base64.b64encode(zlib.compress(raw)).decode()
    mutations = [
        ("unaudited delivery", "matrix decision", matrix_flip),
        ("silence claimed equal", "trace decision", lambda d: d["trace"][0].update(verdict=["EQUAL", 0])),
        ("hidden world substituted", "hidden fixture", lambda d: d["trace"][1].update(remote_fixture=None)),
        ("changed retained proof", "retained evidence", lambda d: d["trace"][8]["proof"].__setitem__(3, "0"*64)),
        ("subprocess crash", "exit", lambda d: d["trace"][4].update(exit=-9)),
        ("independence overstated", "trust", lambda d: d.update(independence="VERIFIED")),
    ]
    rejected = []
    for label, reason, mutate in mutations:
        copy_doc = copy.deepcopy(doc)
        mutate(copy_doc)
        try:
            audit(copy_doc, sha)
        except ValueError as exc:
            require(str(exc) == reason, "wrong audit rejection")
            rejected.append(label)
        else:
            raise ValueError("accepted corrupt report")
    return rejected


if __name__ == "__main__":
    payload = json.loads(Path(sys.argv[1]).read_bytes())
    counts = audit(payload, sys.argv[2])
    print("AUDIT " + json.dumps(dict(schedules=900, decisions=counts, trace=len(TRACE),
                                     rejected=negative_controls(payload, sys.argv[2])), separators=(",", ":")))
