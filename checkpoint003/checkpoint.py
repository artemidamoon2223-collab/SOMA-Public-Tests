"""Verify a synthetic journal against a trust input supplied by its caller."""

import hashlib
import json
import sys
from pathlib import Path

MAX_JOURNAL = 16_384
MAX_CHECKPOINT = 256
MAX_EVENTS = 128


def read_limited(path, limit):
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("oversize")
    return data


def checkpoint(raw):
    value = json.loads(raw)
    if not isinstance(value, dict) or value.keys() != {"generation", "sha256"}:
        raise ValueError("checkpoint schema")
    generation, digest = value["generation"], value["sha256"]
    if type(generation) is not int or not 1 <= generation <= MAX_EVENTS:
        raise ValueError("generation")
    if not isinstance(digest, str) or len(digest) != 64 or set(digest) - set("0123456789abcdef"):
        raise ValueError("digest")
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    if raw != canonical:
        raise ValueError("checkpoint encoding")
    return generation, digest


def journal_head(raw):
    rows = raw.splitlines(keepends=True)
    if not 1 <= len(rows) <= MAX_EVENTS:
        raise ValueError("journal length")
    for sequence, line in enumerate(rows, start=1):
        record = json.loads(line)
        if not isinstance(record, dict) or record.keys() != {"seq", "event"}:
            raise ValueError("journal schema")
        if type(record["seq"]) is not int or record["seq"] != sequence:
            raise ValueError("sequence")
        if not isinstance(record["event"], str) or not 1 <= len(record["event"]) <= 64:
            raise ValueError("event")
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        if line != canonical:
            raise ValueError("journal encoding")
    return len(rows), hashlib.sha256(raw).hexdigest()


def verify(root, trusted_raw):
    if not trusted_raw:
        return "MISSING_TRUST"
    try:
        if len(trusted_raw) > MAX_CHECKPOINT:
            raise ValueError("oversize")
        trusted = checkpoint(trusted_raw)
    except (ValueError, RecursionError):
        return "INVALID_TRUST"
    try:
        journal = journal_head(read_limited(root / "events.jsonl", MAX_JOURNAL))
        anchor = checkpoint(read_limited(root / "anchor.json", MAX_CHECKPOINT))
    except FileNotFoundError:
        return "MISSING_LOCAL"
    except (OSError, ValueError, RecursionError):
        return "INVALID_LOCAL"
    if journal != anchor:
        return "LOCAL_MISMATCH"
    if journal[0] < trusted[0]:
        return "ROLLBACK"
    if journal[0] > trusted[0]:
        return "UNCONFIRMED_ADVANCE"
    if journal[1] != trusted[1]:
        return "FORK"
    return "ACCEPT"


def main():
    if len(sys.argv) != 2:
        return 2
    code = verify(Path(sys.argv[1]), sys.stdin.buffer.read(MAX_CHECKPOINT + 1))
    print(json.dumps({"code": code}, sort_keys=True))
    return 0 if code == "ACCEPT" else 3


if __name__ == "__main__":
    raise SystemExit(main())
