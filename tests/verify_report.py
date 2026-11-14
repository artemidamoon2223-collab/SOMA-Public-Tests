"""Separate report checker with adversarial controls; standard library only."""
import collections
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "platform_inventory", "af_unix_peer_credentials", "process_separation",
    "permissions_locks_atomic_replace", "sqlite_sigkill_recovery",
    "sqlite_concurrent_writes", "resource_limit_enforcement",
    "unprivileged_user_namespace", "unprivileged_mount_namespace",
    "durable_action_identity_and_authorization", "unknown_outcome_never_replays",
    "concurrent_action_claims", "append_only_journal_and_tamper_controls",
    "concurrent_journal_appends",
}
OPTIONAL = {"unprivileged_user_namespace", "unprivileged_mount_namespace", "af_unix_peer_credentials"}
SOURCES = {"synthetic_store.py", "tests/preflight.py", "tests/verify_report.py"}


def verify(report):
    assert report["schema"] == "SOMA_PUBLIC_CI_001_V1"
    assert report["scope"] == "PUBLIC_SYNTHETIC_ONLY"
    assert report["SCIENTIFICALLY_VALIDATED"] == "NO"
    assert report["CONFIRMATORY_SET_USED"] is False
    assert report["NEW_LIVE_MODEL_CALLS"] == 0
    assert report["production_isolation_verified"] is False
    rows = report["results"]
    assert len(rows) == len(EXPECTED)
    assert {row["name"] for row in rows} == EXPECTED
    assert report["counts"] == dict(collections.Counter(row["status"] for row in rows))
    for row in rows:
        assert row["status"] in {"PASS", "FAIL", "BLOCKED", "UNSUPPORTED", "SKIPPED"}
        assert row["name"] in OPTIONAL or row["status"] == "PASS"
        assert row["status"] != "FAIL"
        assert row["seconds"] >= 0 and row["detail"]
    assert set(report["source_sha256"]) == SOURCES
    for name, digest in report["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    by_name = {row["name"]: row["detail"] for row in rows}
    assert by_name["platform_inventory"]["python"].startswith("3.12.")
    if next(row for row in rows if row["name"] == "af_unix_peer_credentials")["status"] == "PASS":
        assert by_name["af_unix_peer_credentials"]["bidirectional_peer_pid_uid_gid"] is True
    assert by_name["sqlite_concurrent_writes"]["committed_unique_rows"] == 60
    assert by_name["unknown_outcome_never_replays"]["side_effect_count"] == 1
    assert by_name["unknown_outcome_never_replays"]["restart_attempts"] == 3
    assert by_name["concurrent_action_claims"]["executions"] == 1
    assert by_name["concurrent_journal_appends"]["complete_unique_records"] == 48
    assert set(by_name["append_only_journal_and_tamper_controls"]["negative_controls_rejected"]) == {
        "edit", "truncate", "missing_anchor", "wrong_anchor", "torn_append"}


def main(path):
    report = json.loads(Path(path).read_text())
    verify(report)
    mutations = []
    missing = copy.deepcopy(report)
    missing["results"].pop()
    mutations.append(("missing_case", missing))
    false_count = copy.deepcopy(report)
    false_count["counts"]["PASS"] = 1000
    mutations.append(("false_success_count", false_count))
    altered_hash = copy.deepcopy(report)
    altered_hash["source_sha256"]["synthetic_store.py"] = "0" * 64
    mutations.append(("wrong_source_hash", altered_hash))
    replay = copy.deepcopy(report)
    next(row for row in replay["results"] if row["name"] == "unknown_outcome_never_replays")["detail"]["side_effect_count"] = 2
    mutations.append(("replay_evidence", replay))
    caught = []
    for name, mutant in mutations:
        try:
            verify(mutant)
        except (AssertionError, KeyError):
            caught.append(name)
        else:
            raise AssertionError("verifier accepted " + name)
    result = {"status": "PASS", "negative_controls_rejected": caught,
              "report_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
              "scope": "report structure, source binding and evidence consistency; not production verification"}
    Path(path).with_name("verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print("VERIFICATION_JSON " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
