"""Bounded public Linux probes and newly written synthetic invariants.

No production code, private fixtures, network calls, sudo or model packages.
Every child has a timeout. Resource probes lower their own limits only.
"""
import argparse
import collections
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import socket
import sqlite3
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from synthetic_store import ActionStore, IntegrityError, Journal, atomic_write

CASES = []


class Unavailable(Exception):
    def __init__(self, status, detail):
        self.status, self.detail = status, detail


def case(category):
    def register(function):
        CASES.append((category, function))
        return function
    return register


def start(role, *args, pass_fds=()):
    return subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()),
                             "--worker", role, *map(str, args)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, pass_fds=pass_fds, start_new_session=True)


def finish(process, expected=0, timeout=12):
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        out, err = process.communicate()
        raise AssertionError("child timeout; process group terminated")
    assert process.returncode == expected, (process.returncode, out[-3000:], err[-3000:])
    return json.loads(out) if out.strip() else {}


def rejected(function, exception):
    try:
        function()
    except exception:
        return
    raise AssertionError("negative control was accepted")


def child(role, args):
    if role == "peer":
        with socket.socket(socket.AF_UNIX) as stream:
            stream.settimeout(5)
            stream.connect(args[0])
            peer = struct.unpack("3i", stream.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            stream.sendall(b"public-ping")
            assert stream.recv(100) == b"public-pong"
            print(json.dumps({"server": peer, "pid": os.getpid(), "uid": os.getuid(), "gid": os.getgid()}))
    elif role == "lock":
        with open(args[0], "a+b") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = "acquired"
            except BlockingIOError:
                result = "blocked"
            print(json.dumps({"lock": result}))
    elif role == "identity":
        os.environ["PUBLIC_FIXTURE_CHILD"] = "changed"
        os.chdir(args[0])
        print(json.dumps({"pid": os.getpid(), "ppid": os.getppid(), "sid": os.getsid(0), "cwd": os.getcwd()}))
    elif role == "sqlite":
        db = sqlite3.connect(args[0], timeout=3, isolation_level=None)
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO evidence VALUES (?, ?)", (args[1], "public-fixture"))
        if args[2] == "after":
            db.commit()
        os.kill(os.getpid(), signal.SIGKILL)
    elif role == "sql_concurrent":
        db = sqlite3.connect(args[0], timeout=3, isolation_level=None)
        db.execute("PRAGMA synchronous=FULL")
        for index in range(15):
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO evidence VALUES (?, ?)", (args[1] + "-" + str(index), "public-fixture"))
            db.commit()
        db.close()
        print(json.dumps({"commits": 15}))
    elif role == "journal":
        journal = Journal(args[0])
        for index in range(12):
            journal.append({"worker": args[1], "index": index})
        print(json.dumps({"appended": 12}))
    elif role == "action":
        store = ActionStore(args[0])
        store.reserve("public-action", {"fixture": 1})
        if store.claim("public-action"):
            with open(args[1], "ab") as receipt:
                receipt.write(b"synthetic-execution\n")
                receipt.flush()
                os.fsync(receipt.fileno())
            if args[2] == "crash":
                os.kill(os.getpid(), signal.SIGKILL)
            store.complete("public-action")
        print(json.dumps({"state": store.state("public-action")}))
        store.close()
    elif role == "memory":
        resource.setrlimit(resource.RLIMIT_AS, (64 * 1024**2, 64 * 1024**2))
        try:
            bytearray(128 * 1024**2)
        except MemoryError:
            print(json.dumps({"memory_limit_enforced": True}))
        else:
            raise AssertionError("allocation unexpectedly permitted")
    elif role == "descriptors":
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
        opened = []
        try:
            for _ in range(64):
                opened.append(os.open(os.devnull, os.O_RDONLY))
        except OSError as error:
            assert error.errno == errno.EMFILE
        else:
            raise AssertionError("descriptor limit not enforced")
        finally:
            for fd in opened:
                os.close(fd)
        with open(os.devnull) as stream:
            stream.read()
        print(json.dumps({"descriptor_limit_enforced": True, "cleanup_recovered": True}))
    elif role == "cpu":
        resource.setrlimit(resource.RLIMIT_CPU, (1, 2))
        while True:
            pass
    elif role == "file_size":
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024, 1024))
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        fd = os.open(args[0], os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            os.write(fd, b"x" * 1024)
            try:
                os.write(fd, b"y")
            except OSError as error:
                assert error.errno == errno.EFBIG
            else:
                raise AssertionError("file size limit not enforced")
        finally:
            os.close(fd)
        assert Path(args[0]).stat().st_size == 1024
        print(json.dumps({"file_size_limit_enforced": True}))
    else:
        raise ValueError("unknown worker role")


@case("capability")
def platform_inventory(directory):
    memory = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.split(":", 1)[0] in ("MemTotal", "MemAvailable"):
            name, value = line.split(":", 1)
            memory[name + "_kib"] = int(value.split()[0])
    assert platform.system() == "Linux"
    assert sys.version_info[:2] == (3, 12)
    return {"distribution": platform.freedesktop_os_release(), "kernel": platform.release(),
            "architecture": platform.machine(), "python": platform.python_version(),
            "cpu_count": os.cpu_count(), "cpu_affinity_count": len(os.sched_getaffinity(0)),
            "ram": memory, "uid": os.getuid(), "euid": os.geteuid(),
            "production_isolation_verified": False}


@case("capability")
def af_unix_peer_credentials(directory):
    if not hasattr(socket, "SO_PEERCRED"):
        raise Unavailable("UNSUPPORTED", "SO_PEERCRED unavailable")
    try:
        server = socket.socket(socket.AF_UNIX)
    except PermissionError as error:
        raise Unavailable("BLOCKED", {"errno": error.errno, "operation": "AF_UNIX socket creation", "no_privileged_retry": True}) from error
    with server:
        server.settimeout(5)
        server.bind(str(directory / "sock"))
        server.listen(1)
        process = start("peer", directory / "sock")
        try:
            with server.accept()[0] as stream:
                stream.settimeout(5)
                peer = struct.unpack("3i", stream.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                assert peer == (process.pid, os.getuid(), os.getgid()), peer
                assert stream.recv(100) == b"public-ping"
                stream.sendall(b"public-pong")
            actual = finish(process)
            assert actual["server"] == [os.getpid(), os.getuid(), os.getgid()]
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
    return {"af_unix": True, "bidirectional_peer_pid_uid_gid": True,
            "cross_uid_authorization": "NOT_VERIFIED"}


@case("capability")
def process_separation(directory):
    before = os.getcwd()
    result = finish(start("identity", directory))
    assert result["pid"] != os.getpid() and result["ppid"] == os.getpid()
    assert result["sid"] == result["pid"] and os.getsid(0) != result["sid"]
    assert result["cwd"] == str(directory) and os.getcwd() == before
    assert "PUBLIC_FIXTURE_CHILD" not in os.environ
    return {"pid_session_cwd_environment_separation": True, "hostile_code_sandbox": "NOT_VERIFIED"}


@case("capability")
def permissions_locks_atomic_replace(directory):
    target = directory / "value"
    target.write_bytes(b"old")
    target.chmod(0o600)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    with target.open("rb") as old:
        atomic_write(target, b"new")
        assert old.read() == b"old" and target.read_bytes() == b"new"
    lock_path = directory / "lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert finish(start("lock", lock_path))["lock"] == "blocked"
    assert finish(start("lock", lock_path))["lock"] == "acquired"
    target.write_bytes(b"A" * 512)
    errors, stop, reads = [], threading.Event(), []
    def read_loop():
        try:
            while not stop.is_set():
                if target.read_bytes() not in (b"A" * 512, b"B" * 512):
                    errors.append("partial replacement")
                if not reads:
                    reads.append(True)
        except Exception:
            errors.append(traceback.format_exc())
    reader = threading.Thread(target=read_loop)
    reader.start()
    try:
        for index in range(20):
            atomic_write(target, (b"A" if index % 2 else b"B") * 512)
    finally:
        stop.set()
        reader.join(3)
    assert not reader.is_alive() and not errors and reads
    return {"mode_0600": True, "interprocess_lock": True, "atomic_reader_view": True,
            "cross_uid_permission_boundary": "NOT_VERIFIED"}


def database(path):
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("CREATE TABLE evidence (id TEXT PRIMARY KEY, payload TEXT)")
    db.commit()
    db.close()


@case("capability")
def sqlite_sigkill_recovery(directory):
    path = directory / "store.sqlite"
    database(path)
    finish(start("sqlite", path, "uncommitted", "before"), expected=-signal.SIGKILL)
    finish(start("sqlite", path, "committed", "after"), expected=-signal.SIGKILL)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT id FROM evidence").fetchall() == [("committed",)]
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    return {"uncommitted_rollback": True, "committed_survives_sigkill": True,
            "power_loss_or_storage_failure": "NOT_VERIFIED"}


@case("capability")
def sqlite_concurrent_writes(directory):
    path = directory / "concurrent.sqlite"
    database(path)
    children = [start("sql_concurrent", path, i) for i in range(4)]
    for process in children:
        assert finish(process)["commits"] == 15
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 60
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    return {"processes": 4, "committed_unique_rows": 60}


@case("capability")
def resource_limit_enforcement(directory):
    results = {role: finish(start(role, directory / "bounded_file"))
               for role in ("memory", "descriptors", "file_size")}
    finish(start("cpu"), expected=-signal.SIGXCPU, timeout=5)
    return dict(results, cpu_limit_signal="SIGXCPU", global_exhaustion_attempted=False)


def namespace_probe(kind):
    if os.geteuid() == 0:
        raise Unavailable("BLOCKED", "root session cannot establish unprivileged capability")
    executable = shutil.which("unshare")
    if not executable:
        raise Unavailable("UNSUPPORTED", "unshare executable missing")
    names = ["user"] if kind == "user" else ["user", "mnt"]
    flags = ["--user"] if kind == "user" else ["--user", "--mount"]
    script = "import os,json;print(json.dumps({n:os.readlink('/proc/self/ns/'+n) for n in " + repr(names) + "}))"
    result = subprocess.run([executable, *flags, "--", sys.executable, "-c", script],
                            capture_output=True, text=True, timeout=5)
    if result.returncode:
        message = result.stderr.strip()[:1000]
        if "Operation not permitted" in message or "Permission denied" in message:
            raise Unavailable("BLOCKED", {"exit_code": result.returncode, "stderr": message, "no_privileged_retry": True})
        if "not supported" in message.lower() or "invalid argument" in message.lower():
            raise Unavailable("UNSUPPORTED", {"exit_code": result.returncode, "stderr": message})
        raise AssertionError((result.returncode, message))
    actual = json.loads(result.stdout)
    assert all(actual[n] != os.readlink("/proc/self/ns/" + n) for n in names)
    return {"new_namespaces": names, "privilege_escalation": False, "mount_operations_tested": False}


@case("optional_capability")
def unprivileged_user_namespace(directory):
    return namespace_probe("user")


@case("optional_capability")
def unprivileged_mount_namespace(directory):
    return namespace_probe("mount")


@case("synthetic_invariant")
def durable_action_identity_and_authorization(directory):
    path = directory / "actions.sqlite"
    store = ActionStore(path)
    store.reserve("fixed", {"input": 1})
    store.close()
    store = ActionStore(path)
    store.reserve("fixed", {"input": 1})
    rejected(lambda: store.reserve("fixed", {"input": 2}), IntegrityError)
    rejected(lambda: store.reserve("unauthorized", {}, "synthetic_delete"), PermissionError)
    assert store.state("unauthorized") is None
    assert store.claim("fixed")
    store.complete("fixed")
    assert not store.claim("fixed") and store.state("fixed") == ("COMPLETED", 1)
    store.close()
    return {"same_id_same_request_idempotent": True, "rebind_rejected": True,
            "unauthorized_operation_has_no_row": True, "duplicate_execution_rejected": True}


@case("synthetic_invariant")
def unknown_outcome_never_replays(directory):
    path, receipt = directory / "actions.sqlite", directory / "receipt"
    finish(start("action", path, receipt, "crash"), expected=-signal.SIGKILL)
    store = ActionStore(path)
    assert store.state("public-action") == ("RUNNING", 1)
    assert store.recover_after_worker_death() == 1
    store.close()
    for _ in range(3):
        result = finish(start("action", path, receipt, "normal"))
        assert result["state"] == ["UNKNOWN_OUTCOME", 1]
    assert receipt.read_bytes() == b"synthetic-execution\n"
    return {"sigkill_verified": True, "restart_attempts": 3, "side_effect_count": 1,
            "unknown_remained_blocked": True}


@case("synthetic_invariant")
def concurrent_action_claims(directory):
    path, receipt = directory / "actions.sqlite", directory / "receipt"
    ActionStore(path).close()
    processes = [start("action", path, receipt, "normal") for _ in range(4)]
    for process in processes:
        finish(process)
    store = ActionStore(path)
    assert store.state("public-action") == ("COMPLETED", 1)
    assert receipt.read_bytes() == b"synthetic-execution\n"
    store.close()
    return {"concurrent_processes": 4, "executions": 1}


@case("synthetic_invariant")
def append_only_journal_and_tamper_controls(directory):
    journal = Journal(directory / "original")
    journal.append({"fixture": 1})
    before = journal.events.read_bytes()
    journal.append({"fixture": 2})
    assert journal.events.read_bytes().startswith(before)
    assert len(journal.verify()) == 2
    caught = []
    for mutation in ("edit", "truncate", "missing_anchor", "wrong_anchor", "torn_append"):
        target = directory / mutation
        shutil.copytree(journal.root, target)
        clone = Journal(target)
        if mutation == "edit":
            clone.events.write_bytes(clone.events.read_bytes().replace(b'"fixture":1', b'"fixture":9'))
        elif mutation == "truncate":
            clone.events.write_bytes(before)
        elif mutation == "missing_anchor":
            clone.anchor.unlink()
        elif mutation == "wrong_anchor":
            clone.anchor.write_text('{"sequence":99,"hash":"wrong"}')
        else:
            with clone.events.open("ab") as stream:
                stream.write(b'{"incomplete":')
        rejected(clone.verify, IntegrityError)
        rejected(lambda: clone.append({"must_not_append": True}), IntegrityError)
        caught.append(mutation)
    return {"existing_prefix_unchanged": True, "negative_controls_rejected": caught,
            "authenticated_journal": False, "coordinated_journal_anchor_rollback_detection": "NOT_VERIFIED"}


@case("synthetic_invariant")
def concurrent_journal_appends(directory):
    journal = Journal(directory / "journal")
    processes = [start("journal", journal.root, index) for index in range(4)]
    for process in processes:
        finish(process)
    rows = journal.verify()
    assert len(rows) == 48
    assert len({(r["payload"]["worker"], r["payload"]["index"]) for r in rows}) == 48
    return {"processes": 4, "complete_unique_records": 48}


def main(output):
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024**2, 8 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    results = []
    for category, function in CASES:
        begin = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="public-ci-") as temporary:
            try:
                detail = function(Path(temporary))
                status = "PASS"
            except Unavailable as error:
                status, detail = error.status, error.detail
            except Exception:
                status, detail = "FAIL", traceback.format_exc()
        row = {"name": function.__name__, "category": category, "status": status,
               "seconds": round(time.monotonic() - begin, 4), "detail": detail}
        results.append(row)
        print("CASE_JSON " + json.dumps(row, sort_keys=True), flush=True)
    counts = dict(collections.Counter(row["status"] for row in results))
    report = {"schema": "SOMA_PUBLIC_CI_001_V1", "scope": "PUBLIC_SYNTHETIC_ONLY",
              "execution_environment": "github_actions" if os.environ.get("GITHUB_ACTIONS") == "true" else "local",
              "commit_sha": os.environ.get("PREFLIGHT_SOURCE_SHA", "local-uncommitted"),
              "github_run_id": os.environ.get("GITHUB_RUN_ID"),
              "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
              "results": results, "counts": counts,
              "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [ROOT / "synthetic_store.py", Path(__file__).resolve(), ROOT / "tests/verify_report.py"]},
              "SCIENTIFICALLY_VALIDATED": "NO", "CONFIRMATORY_SET_USED": False,
              "NEW_LIVE_MODEL_CALLS": 0, "production_isolation_verified": False}
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print("REPORT_JSON " + json.dumps(report, sort_keys=True), flush=True)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
            summary.write("## Public synthetic Linux preflight\n\n" + str(counts) + "\n\n")
            summary.write("| Check | Result |\n|---|---|\n")
            for row in results:
                summary.write("| " + row["name"] + " | " + row["status"] + " |\n")
            summary.write("\nNo production isolation or SOMA correctness claim.\n")
    return 1 if counts.get("FAIL") else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker")
    parser.add_argument("--output", default="results/preflight.json")
    parser.add_argument("arguments", nargs="*")
    options = parser.parse_args()
    if options.worker:
        child(options.worker, options.arguments)
    else:
        raise SystemExit(main(options.output))
