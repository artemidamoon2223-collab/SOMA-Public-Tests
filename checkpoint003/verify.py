"""Exercise the CLI against transport-independent synthetic fixtures."""

import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "checkpoint.py"
# Fixed independent fixtures. The reference digests are computed over these bytes.
FIRST = b'{"event":"start","seq":1}\n'
SECOND = FIRST + b'{"event":"settled","seq":2}\n'
THIRD = SECOND + b'{"event":"reviewed","seq":3}\n'
FORK = FIRST + b'{"event":"alternate","seq":2}\n'


def reference(raw, number):
    digest = hashlib.sha256(raw).hexdigest()
    return f'{{"generation":{number},"sha256":"{digest}"}}\n'.encode()


def insist(accepted, label):
    if not accepted:
        raise AssertionError(label)


def snapshot(folder):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(folder.iterdir())}


def crash_after_journal_replace(folder):
    child = """
import os, pathlib, signal, sys
folder = pathlib.Path(sys.argv[1])
temporary = folder / 'events.tmp'
with temporary.open('wb') as f:
    f.write(sys.stdin.buffer.read())
    f.flush()
    os.fsync(f.fileno())
temporary.replace(folder / 'events.jsonl')
descriptor = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(descriptor)
finally:
    os.close(descriptor)
os.kill(os.getpid(), signal.SIGKILL)
"""
    result = subprocess.run([sys.executable, "-I", "-c", child, str(folder)],
                            input=THIRD, capture_output=True, timeout=5)
    insist(result.returncode == -signal.SIGKILL and not result.stdout and not result.stderr,
           "crash control did not terminate by SIGKILL at the intended point")
    insist((folder / "events.jsonl").read_bytes() == THIRD, "journal write missing")
    insist((folder / "anchor.json").read_bytes() == reference(SECOND, 2), "anchor changed")
    return result.returncode


def run_case(name, journal, anchor, trusted, expected, crash=False):
    with tempfile.TemporaryDirectory(prefix="soma-checkpoint-") as directory:
        folder = Path(directory)
        if journal is not None:
            (folder / "events.jsonl").write_bytes(journal)
        if anchor is not None:
            (folder / "anchor.json").write_bytes(anchor)
        crash_code = crash_after_journal_replace(folder) if crash else None
        before = snapshot(folder)
        result = subprocess.run([sys.executable, "-I", str(CANDIDATE), str(folder)],
                                input=trusted, capture_output=True, timeout=5)
        actual = json.loads(result.stdout)
        unchanged = before == snapshot(folder)
        expected_exit = 0 if expected == "ACCEPT" else 3
        row = {"case": name, "expected": expected, "actual": actual.get("code"),
               "exit": result.returncode, "unchanged": unchanged, "crash_exit": crash_code}
        print("CASE_JSON " + json.dumps(row, sort_keys=True), flush=True)
        insist(actual == {"code": expected} and result.returncode == expected_exit
               and not result.stderr and unchanged, name)
        return row


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (192 * 1024**2,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))
    current = reference(SECOND, 2)
    newer = reference(THIRD, 3)
    cases = [
        ("current", SECOND, current, current, "ACCEPT"),
        ("trusted_advance", THIRD, newer, newer, "ACCEPT"),
        ("paired_rollback", FIRST, reference(FIRST, 1), current, "ROLLBACK"),
        ("same_generation_fork", FORK, reference(FORK, 2), current, "FORK"),
        ("paired_unconfirmed_advance", THIRD, newer, current, "UNCONFIRMED_ADVANCE"),
        ("no_trust_input", SECOND, current, b"", "MISSING_TRUST"),
        ("malformed_trust_input", SECOND, current, b"[]\n", "INVALID_TRUST"),
        ("missing_anchor", SECOND, None, current, "MISSING_LOCAL"),
        ("corrupt_local_anchor", SECOND, b"{\n", current, "INVALID_LOCAL"),
        ("oversize_journal", b"x" * 16_385, current, current, "INVALID_LOCAL"),
        ("corrupt_local_journal", SECOND[:-1], current, current, "INVALID_LOCAL"),
        ("sigkill_between_writes", SECOND, current, current, "LOCAL_MISMATCH", True),
    ]
    rows = [run_case(*case) for case in cases]
    report = {
        "schema": "SOMA_PUBLIC_CHECKPOINT_003_V1",
        "source_sha": os.environ.get("SOURCE_SHA", "local"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "python": sys.version.split()[0],
        "euid": os.geteuid(),
        "records": rows,
        "programs": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in (CANDIDATE, Path(__file__))},
        "SCIENTIFICALLY_VALIDATED": "NO",
        "CONFIRMATORY_SET_USED": False,
        "NEW_LIVE_MODEL_CALLS": 0,
    }
    print("REPORT_JSON " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
