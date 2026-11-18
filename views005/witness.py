"""Pairwise comparison of authenticated, bounded synthetic observations."""
import hmac
import json
from pathlib import Path
import re
import sys

STREAM = "tiles-v1"
PEER = {"left": "right", "right": "left"}


def packed(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def attest(role, view, turn, keys):
    body = [STREAM, role, turn, view]
    return [body, hmac.digest(keys[role], packed(body), "sha256").hex()]


def inspect(packet, role, turn, keys):
    if not isinstance(packet, list) or len(packet) != 2:
        return "INVALID", None
    body, tag = packet
    if not isinstance(body, list) or len(body) != 4 or not isinstance(tag, str):
        return "INVALID", None
    stream, sender, epoch, history = body
    if (stream != STREAM or sender != role or type(epoch) is not int
            or not isinstance(history, str) or not re.fullmatch("[AB]{0,3}", history)
            or not re.fullmatch("[a-f0-9]{64}", tag)):
        return "INVALID", None
    if not hmac.compare_digest(tag, hmac.digest(keys[role], packed(body), "sha256").hex()):
        return "INVALID", None
    if epoch != turn:
        return "STALE", None
    return "OK", history


def compare(role, turn, own, other, keys):
    status, local = inspect(own, role, turn, keys)
    if status != "OK":
        return status, 0
    if other is None:
        return "UNKNOWN", 0
    status, remote = inspect(other, PEER[role], turn, keys)
    if status != "OK":
        return status, 0
    for position, (a, b) in enumerate(zip(local, remote), start=1):
        if a != b:
            return "FORK", position
    return ("EQUAL" if local == remote else "PREFIX"), 0


def retained(path, role, turn, own, other, keys):
    if path.exists():
        proof = json.loads(path.read_bytes())
        old_turn, local, remote = proof
        status, pos = compare(role, old_turn, local, remote, keys)
        if status != "FORK":
            return "INVALID_STORE", 0
        return "KNOWN_FORK", pos
    status, pos = compare(role, turn, own, other, keys)
    if status == "FORK":
        staging = path.with_suffix(".tmp")
        staging.write_bytes(packed([turn, own, other]))
        staging.replace(path)
    return status, pos


if __name__ == "__main__":
    # Root is a temporary single-writer fixture directory selected by the harness.
    root = Path(sys.argv[1])
    role, turn, peer = json.load(sys.stdin)
    own = json.loads((root / role / "own.json").read_bytes())
    keys = {r: (root / (r + ".key")).read_bytes() for r in PEER}
    verdict, position = retained(root / role / "proof.json", role, turn, own, peer, keys)
    print(json.dumps([verdict, position]))
    sys.exit(3 if verdict in {"INVALID", "STALE", "INVALID_STORE"} else 0)
