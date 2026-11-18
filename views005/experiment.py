"""Generate observed outcomes. The independent oracle lives in audit.py."""
import base64
import hashlib
import itertools
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import zlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import witness
sys.path.pop(0)

FILES = (".github/workflows/soma-views-005.yml", "views005/README.md",
         "views005/witness.py", "views005/experiment.py", "views005/audit.py")


def matrix(keys):
    rows = []
    words = ["".join(p) for n in range(4) for p in itertools.product("AB", repeat=n)]
    for index, (left, right) in enumerate(itertools.product(words, repeat=2), start=1):
        turn = index
        a = witness.attest("left", left, turn, keys)
        b = witness.attest("right", right, turn, keys)
        for mask in range(4):
            x = witness.compare("left", turn, a, b if mask & 1 else None, keys)
            y = witness.compare("right", turn, b, a if mask & 2 else None, keys)
            row = (left or "-", right or "-", mask, *x, *y)
            rows.append("\t".join(map(str, row)))
    raw = ("\n".join(rows) + "\n").encode()
    return base64.b64encode(zlib.compress(raw, 9)).decode()


def trace(root, keys):
    for role in keys:
        (root / role).mkdir()
        (root / (role + ".key")).write_bytes(keys[role])
    entries = []

    def put(role, view, turn=1):
        packet = witness.attest(role, view, turn, keys)
        (root / role / "own.json").write_bytes(witness.packed(packet))
        return packet

    def call(label, role, turn, peer):
        path = root / role / "proof.json"
        own_path = root / role / "own.json"
        raw_input = witness.packed([role, turn, peer])
        p = subprocess.run([sys.executable, "-I", "-B", str(HERE / "witness.py"), str(root)],
                           input=raw_input, capture_output=True, timeout=3)
        stored = json.loads(path.read_bytes()) if path.exists() else None
        proof = None
        if stored is not None:
            old, a, b = stored
            proof = [old, a[0], b[0], hashlib.sha256(path.read_bytes()).hexdigest()]
        row = dict(label=label, role=role, turn=turn, local=json.loads(own_path.read_bytes())[0],
                   peer=peer[0] if peer else None, verdict=json.loads(p.stdout), exit=p.returncode,
                   stderr=p.stderr.decode(), proof=proof,
                   input_digest=hashlib.sha256(own_path.read_bytes()+b"\n"+raw_input).hexdigest())
        remote = root / witness.PEER[role] / "own.json"
        row["remote_fixture"] = json.loads(remote.read_bytes())[0] if remote.exists() else None
        entries.append(row)
        print("TRACE " + json.dumps(row, separators=(",", ":")), file=sys.stderr, flush=True)

    left = put("left", "ABA")
    put("right", "ABA")
    call("honest-world-hidden", "left", 1, None)
    right = put("right", "ABB")
    call("forked-world-hidden", "left", 1, None)
    call("other-observer-hidden", "right", 1, None)
    call("reflection", "right", 1, right)
    broken = json.loads(json.dumps(left))
    broken[0][3] = "AAA"
    call("altered", "right", 1, broken)
    call("delivered-right", "right", 1, left)
    call("still-hidden-left", "left", 1, None)
    call("delivered-left", "left", 1, right)
    put("left", "A", 2)
    put("right", "A", 2)
    call("restart-left-withheld", "left", 2, None)
    call("restart-right-withheld", "right", 2, None)
    # A fresh observer store for the stale-message control and compatible advance.
    clean = root / "fresh"
    clean.mkdir()
    root = clean
    for role, key in keys.items():
        (root / role).mkdir()
        (root / (role + ".key")).write_bytes(key)
    put("left", "AB", 2)
    call("old-round", "left", 2, right)
    extension = put("right", "ABA", 2)
    call("prefix", "left", 2, extension)
    equal = put("right", "AB", 2)
    call("equal", "left", 2, equal)
    return entries


if __name__ == "__main__":
    keys = {name: secrets.token_bytes(32) for name in ("left", "right")}
    with tempfile.TemporaryDirectory() as tmp:
        report = dict(schema=1, commit=os.environ["SOURCE_SHA"], matrix=matrix(keys),
                      trace=trace(Path(tmp), keys), independence="NOT_VERIFIED",
                      files={p: hashlib.sha256((HERE.parent / p).read_bytes()).hexdigest() for p in FILES})
    print(json.dumps(report, separators=(",", ":")))
