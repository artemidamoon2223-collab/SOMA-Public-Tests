"""Synthetic checkpoint publication and read-only recovery."""
import hashlib
import hmac
import json
import os
import re
import signal
import sqlite3
import sys
from pathlib import Path


class Reject(ValueError):
    pass


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(actions):
    return [len(actions), hashlib.sha256(encode(actions)).hexdigest()]


def mac(key, domain, body):
    return hmac.digest(key, domain + b"\0" + encode(body), "sha256").hex()


def valid_hex(value, size):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % size, value) is not None


def valid_head(value):
    return (isinstance(value, list) and len(value) == 2 and type(value[0]) is int
            and 0 <= value[0] <= 64 and valid_hex(value[1], 64))


def valid_action(value):
    return isinstance(value, str) and re.fullmatch("[a-z]{1,12}", value) is not None


def initialize(db):
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE actions (position INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL)")


def history(conn):
    return [row[0] for row in conn.execute("SELECT name FROM actions ORDER BY position")]


def advance(db, key, parent, name, tag, boundary=None):
    if not valid_action(name) or not valid_head(parent):
        raise Reject("BAD_REQUEST")
    if not valid_hex(tag, 64) or not hmac.compare_digest(tag, mac(key, b"append", [parent, name])):
        raise Reject("UNAUTHORIZED")
    with sqlite3.connect(db, isolation_level=None, timeout=3) as conn:
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("BEGIN IMMEDIATE")
        actions = history(conn)
        if name in actions:
            raise Reject("REUSED_ACTION")
        if parent != digest(actions):
            raise Reject("PARENT_CHANGED")
        if len(actions) >= 64:
            raise Reject("FULL")
        conn.execute("INSERT INTO actions(name) VALUES (?)", (name,))
        if boundary == "before":
            os.kill(os.getpid(), signal.SIGKILL)
        conn.commit()
        if boundary == "after":
            os.kill(os.getpid(), signal.SIGKILL)
    return "APPENDED"


def observe(db, key, challenge):
    with sqlite3.connect(db) as conn:
        body = [challenge, digest(history(conn))]
    return [body, mac(key, b"observe", body)]


def read_observation(packet, key, challenge):
    if packet is None:
        raise Reject("MISSING_OBSERVATION")
    if not isinstance(packet, list) or len(packet) != 2:
        raise Reject("MALFORMED_OBSERVATION")
    body, tag = packet
    if (not isinstance(body, list) or len(body) != 2 or not valid_hex(body[0], 32)
            or not valid_head(body[1]) or not valid_hex(tag, 64)):
        raise Reject("MALFORMED_OBSERVATION")
    if not hmac.compare_digest(tag, mac(key, b"observe", body)):
        raise Reject("BAD_OBSERVATION_MAC")
    if body[0] != challenge:
        raise Reject("STALE_CHALLENGE")
    return body[1]


def verify(actions, anchor, floor, challenge, packets, key):
    if not valid_head(floor) or not valid_hex(challenge, 32):
        raise Reject("BAD_VERIFIER_INPUT")
    if not isinstance(packets, list) or len(packets) not in (1, 2):
        raise Reject("MISSING_OBSERVATION")
    heads = [read_observation(packet, key, challenge) for packet in packets]
    head = heads[0]
    if any(other != head for other in heads):
        raise Reject("CONFLICT")
    if head[0] < floor[0]:
        raise Reject("BELOW_FLOOR")
    if (not isinstance(actions, list) or len(actions) > 64 or not all(map(valid_action, actions))
            or len(set(actions)) != len(actions)):
        raise Reject("BAD_JOURNAL")
    actual = digest(actions)
    if not valid_head(anchor) or actual != anchor:
        raise Reject("LOCAL_ANCHOR")
    if head != actual:
        raise Reject("AUTHORITY_MISMATCH")
    if digest(actions[:floor[0]]) != floor:
        raise Reject("FLOOR_FORK")
    return "ACCEPT"


def main():
    # The harness stages bounded JSON inputs in a fresh private temporary directory.
    root = Path.cwd()
    keys = (root / "fixture.keys").read_bytes()
    if sys.argv[2:] == ["--ready"]:
        print("READY", flush=True)
    try:
        args = json.load(sys.stdin)
    except (ValueError, UnicodeError):
        print("MALFORMED_ENVELOPE")
        return 3
    try:
        if sys.argv[1] == "verify":
            result = verify(*args, keys[32:])
        elif sys.argv[1] == "observe":
            print(json.dumps(observe(root / "authority.db", keys[32:], *args)))
            return 0
        elif sys.argv[1] == "advance":
            result = advance(root / "authority.db", keys[:32], *args)
        else:
            raise ValueError("unexpected operation")
    except Reject as error:
        print(str(error))
        return 3
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
