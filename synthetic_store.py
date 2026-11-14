"""New public teaching fixtures. Not SOMA production code or a security boundary.

The journal is hash-linked, not authenticated. An attacker rewriting both the
journal and anchor can forge/roll back it. SQLite fsync is not a power-loss proof.
"""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def atomic_write(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + ".new")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class IntegrityError(ValueError):
    pass


class Journal:
    def __init__(self, directory):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.events = self.root / "events.jsonl"
        self.anchor = self.root / "anchor.json"

    def verify(self):
        raw = self.events.read_bytes() if self.events.exists() else b""
        if raw and not raw.endswith(b"\n"):
            raise IntegrityError("torn journal record")
        previous = "0" * 64
        rows = []
        try:
            for line in raw.splitlines():
                row = json.loads(line)
                body = {k: row[k] for k in ("sequence", "previous", "payload")}
                digest = hashlib.sha256(canonical(body)).hexdigest()
                if (set(row) != {"sequence", "previous", "payload", "hash"}
                        or row["sequence"] != len(rows) + 1
                        or row["previous"] != previous or row["hash"] != digest):
                    raise IntegrityError("journal chain mismatch")
                rows.append(row)
                previous = digest
            expected = {"sequence": len(rows), "hash": previous}
            if rows or self.anchor.exists():
                if json.loads(self.anchor.read_bytes()) != expected:
                    raise IntegrityError("journal/anchor mismatch")
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise IntegrityError("missing or malformed evidence") from error
        return rows

    def append(self, payload):
        with (self.root / "writer.lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            rows = self.verify()
            body = {"sequence": len(rows) + 1,
                    "previous": rows[-1]["hash"] if rows else "0" * 64,
                    "payload": payload}
            row = dict(body, hash=hashlib.sha256(canonical(body)).hexdigest())
            with self.events.open("ab") as stream:
                stream.write(canonical(row) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            atomic_write(self.anchor, canonical({"sequence": row["sequence"], "hash": row["hash"]}))
            return row


class ActionStore:
    """Synthetic one-shot action accounting. No worker permissions are granted."""
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=3, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, state TEXT NOT NULL, executions INTEGER NOT NULL CHECK(executions BETWEEN 0 AND 1))")

    @contextlib.contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.rollback()
            raise
        else:
            self.db.commit()

    def reserve(self, action_id, request, operation="synthetic_read"):
        if operation != "synthetic_read":
            raise PermissionError("operation outside synthetic allowlist")
        if not isinstance(action_id, str) or not action_id:
            raise ValueError("missing action identity")
        digest = hashlib.sha256(canonical(request)).hexdigest()
        with self.transaction():
            old = self.db.execute("SELECT request_hash FROM actions WHERE id=?", (action_id,)).fetchone()
            if old and old[0] != digest:
                raise IntegrityError("action identity rebound")
            self.db.execute("INSERT OR IGNORE INTO actions VALUES (?, ?, 'RESERVED', 0)", (action_id, digest))

    def claim(self, action_id):
        with self.transaction():
            changed = self.db.execute("UPDATE actions SET state='RUNNING', executions=executions+1 WHERE id=? AND state='RESERVED'", (action_id,)).rowcount
        return changed == 1

    def complete(self, action_id):
        with self.transaction():
            if self.db.execute("UPDATE actions SET state='COMPLETED' WHERE id=? AND state='RUNNING'", (action_id,)).rowcount != 1:
                raise IntegrityError("invalid completion")

    def recover_after_worker_death(self):
        # Caller must establish that the old worker is dead; this is not a lease.
        with self.transaction():
            return self.db.execute("UPDATE actions SET state='UNKNOWN_OUTCOME' WHERE state='RUNNING'").rowcount

    def state(self, action_id):
        return self.db.execute("SELECT state, executions FROM actions WHERE id=?", (action_id,)).fetchone()

    def close(self):
        self.db.close()
