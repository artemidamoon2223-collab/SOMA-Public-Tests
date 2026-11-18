"""Black-box challenge driver. Temporary fixture keys are never printed."""
import concurrent.futures
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FILES = ["authority004/protocol.py", "authority004/challenge.py", "authority004/audit.py",
         "authority004/README.md", ".github/workflows/soma-checkpoint-004.yml"]
CMD = [sys.executable, "-I", "-B", str(HERE / "protocol.py")]


def canon(obj):
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()


def head(actions):
    return [len(actions), hashlib.sha256(canon(actions)).hexdigest()]


def result(p):
    return [p.returncode, p.stdout.strip(), p.stderr.strip()]


def invoke(root, op, args):
    return subprocess.run(CMD + [op], cwd=root, input=json.dumps(args), text=True,
                          capture_output=True, timeout=6)


class Fixture:
    def __init__(self, root):
        self.root = root
        self.db = root / "authority.db"
        self.keys = secrets.token_bytes(64)
        (root / "fixture.keys").write_bytes(self.keys)
        # Bootstrap is explicit and permitted only for a new synthetic authority.
        sys.path.insert(0, str(HERE))
        import protocol
        sys.path.pop(0)
        protocol.initialize(self.db)
        self.rows = []

    def writer(self, old, name, boundary=None, wrong=False):
        body = [head(old), name]
        key = self.keys[32:] if wrong else self.keys[:32]
        return [*body, hmac.digest(key, b"append\0" + canon(body), "sha256").hex(), boundary]

    def packet(self, nonce, root=None):
        p = invoke(root or self.root, "observe", [nonce])
        if p.returncode or p.stderr:
            raise RuntimeError("observation process failed")
        return json.loads(p.stdout)

    def row(self, name, calls):
        # Independent DB query after all children have finished, including SIGKILL.
        with sqlite3.connect(self.db) as db:
            actions = [r[0] for r in db.execute("SELECT name FROM actions ORDER BY position")]
            health = db.execute("PRAGMA integrity_check").fetchone()[0]
        row = dict(name=name, calls=calls, durable_actions=actions, sqlite=health)
        self.rows.append(row)
        print("CASE " + json.dumps(row, separators=(",", ":")), file=sys.stderr, flush=True)

    def append(self, case, old, name, boundary=None, wrong=False):
        self.row(case, [result(invoke(self.root, "advance", self.writer(old, name, boundary, wrong)))])

    def check(self, case, actions, floor, nonce, packets, anchor=None):
        args = [actions, head(actions) if anchor is None else anchor, head(floor), nonce, packets]
        self.row(case, [result(invoke(self.root, "verify", args))])

    def snapshot(self, filename):
        with sqlite3.connect(self.db) as db, sqlite3.connect(filename) as snap:
            db.backup(snap)

    def race(self):
        with sqlite3.connect(self.db) as lock:
            lock.execute("BEGIN IMMEDIATE")
            children = [subprocess.Popen(CMD + ["advance", "--ready"], cwd=self.root,
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True) for _ in range(2)]
            try:
                # Both processes are alive in the protocol before releasing their parent.
                if [p.stdout.readline().strip() for p in children] != ["READY", "READY"]:
                    raise RuntimeError("contenders did not reach the barrier")
                with concurrent.futures.ThreadPoolExecutor(2) as pool:
                    futures = [pool.submit(p.communicate, json.dumps(self.writer(["alpha"], n)), 5)
                               for p, n in zip(children, ["beta", "gamma"])]
                    lock.rollback()
                    calls = []
                    for p, future in zip(children, futures):
                        out, err = future.result()
                        calls.append([p.returncode, out.strip(), err.strip()])
            finally:
                for p in children:
                    if p.poll() is None:
                        p.kill()
                    p.wait()
        self.row("concurrent_parent", calls)
        winners = [name for name, call in zip(["beta", "gamma"], calls) if call == [0, "APPENDED", ""]]
        if len(winners) != 1:
            raise RuntimeError("expected one winner")
        return winners[0]


def challenge(root):
    f = Fixture(root)
    fresh = lambda: secrets.token_hex(16)
    f.append("writer_grant", [], "alpha")
    f.snapshot(root / "retained.db")
    a = ["alpha"]
    old_nonce = fresh()
    old = f.packet(old_nonce)
    f.append("wrong_writer", a, "gamma", wrong=True)
    win = f.race()
    current = a + [win]
    nonce = fresh()
    f.check("current", current, a, nonce, [f.packet(nonce)])
    nonce = fresh()
    f.check("rollback_pair", a, a, nonce, [f.packet(nonce)])
    alternate = ["other", win]
    nonce = fresh()
    f.check("replacement_pair", alternate, a, nonce, [f.packet(nonce)])
    f.check("authenticated_stale", current, a, fresh(), [old])
    nonce = fresh()
    f.check("lost_anchor_write", current, a, nonce, [f.packet(nonce)], anchor=head(a))
    nonce = fresh()
    f.check("missing", current, a, nonce, [None])
    f.check("malformed", current, a, fresh(), [[["bad"], "abcd"]])
    nonce = fresh()
    packet = f.packet(nonce)
    packet[0][1] = head(alternate)
    f.check("altered_mac", alternate, a, nonce, [packet])

    # Create an isolated logical snapshot with both roles on the same host.
    shadow = root / "shadow"
    shadow.mkdir()
    (shadow / "fixture.keys").write_bytes(f.keys)
    with sqlite3.connect(root / "retained.db") as snap, sqlite3.connect(shadow / "authority.db") as db:
        snap.backup(db)
    nonce = fresh()
    f.check("fresh_below_floor", a, current, nonce, [f.packet(nonce, shadow)])
    nonce = fresh()
    f.check("common_domain_counterexample", a, a, nonce, [f.packet(nonce, shadow)])
    forkname = "delta"
    fork = a + [forkname]
    q = invoke(shadow, "advance", f.writer(a, forkname))
    if result(q) != [0, "APPENDED", ""]:
        raise RuntimeError("fork fixture could not be staged")
    nonce = fresh()
    f.check("conflicting_observations", current, a, nonce, [f.packet(nonce), f.packet(nonce, shadow)])
    nonce = fresh()
    f.check("fork_at_floor", fork, current, nonce, [f.packet(nonce, shadow)])

    f.append("killed_before_commit", current, "later", boundary="before")
    nonce = fresh()
    f.check("restart_before_commit", current, current, nonce, [f.packet(nonce)])
    f.append("killed_after_commit", current, "later", boundary="after")
    updated = current + ["later"]
    nonce = fresh()
    f.check("incomplete_local_recovery", current, current, nonce, [f.packet(nonce)])
    nonce = fresh()
    f.check("restart_after_commit", updated, current, nonce, [f.packet(nonce)])
    f.append("reused_identity", updated, "later")
    torn = subprocess.run(CMD + ["verify"], cwd=root, input='[["alpha"],',
                          text=True, capture_output=True, timeout=6)
    f.row("truncated_envelope", [result(torn)])
    return f.rows


if __name__ == "__main__":
    commit = os.environ.get("SOURCE_SHA") or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory() as directory:
        cases = challenge(Path(directory))
    print(json.dumps({"schema": 1, "commit": commit, "cases": cases,
                      "files": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in FILES},
                      "authority_independence": "NOT_VERIFIED"}, separators=(",", ":")))
