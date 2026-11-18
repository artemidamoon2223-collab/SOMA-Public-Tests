"""Audit a checkpoint run from the GitHub job log without running its tests."""

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = {
    "current": "ACCEPT",
    "trusted_advance": "ACCEPT",
    "paired_rollback": "ROLLBACK",
    "same_generation_fork": "FORK",
    "paired_unconfirmed_advance": "UNCONFIRMED_ADVANCE",
    "no_trust_input": "MISSING_TRUST",
    "malformed_trust_input": "INVALID_TRUST",
    "missing_anchor": "MISSING_LOCAL",
    "corrupt_local_anchor": "INVALID_LOCAL",
    "oversize_journal": "INVALID_LOCAL",
    "corrupt_local_journal": "INVALID_LOCAL",
    "sigkill_between_writes": "LOCAL_MISMATCH",
}


def verify(report, observed_cases, source_sha, run_id, program_hashes):
    if (report["schema"] != "SOMA_PUBLIC_CHECKPOINT_003_V1"
            or report["source_sha"] != source_sha
            or report["run_id"] != str(run_id)
            or report["programs"] != program_hashes
            or not report["python"].startswith("3.12.")
            or type(report["euid"]) is not int or report["euid"] <= 0
            or report["SCIENTIFICALLY_VALIDATED"] != "NO"
            or report["CONFIRMATORY_SET_USED"] is not False
            or report["NEW_LIVE_MODEL_CALLS"] != 0):
        raise ValueError("Run identity, source hashes, environment, or scope mismatch")
    records = report["records"]
    if records != observed_cases or len(records) != len(EXPECTED):
        raise ValueError("Reported cases differ from the job output")
    by_name = {row["case"]: row for row in records}
    if by_name.keys() != EXPECTED.keys():
        raise ValueError("Missing or duplicate scenario")
    for name, code in EXPECTED.items():
        expected = {"case": name, "expected": code, "actual": code,
                    "exit": 0 if code == "ACCEPT" else 3, "unchanged": True,
                    "crash_exit": -9 if name == "sigkill_between_writes" else None}
        if by_name[name] != expected:
            raise ValueError(f"Wrong result for {name}")


def parse_log(data):
    lines = data.splitlines()
    reports = [json.loads(line.split(" REPORT_JSON ", 1)[1]) for line in lines if " REPORT_JSON " in line]
    cases = [json.loads(line.split(" CASE_JSON ", 1)[1]) for line in lines if " CASE_JSON " in line]
    if len(reports) != 1 or "Contents: read" not in data or "Metadata: read" not in data:
        raise ValueError("Missing run report or read-only permission markers")
    return reports[0], cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--run", required=True, type=int)
    arguments = parser.parse_args()
    folder = Path(__file__).resolve().parent
    program_hashes = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                      for name in ("checkpoint.py", "verify.py")}
    report, cases = parse_log(arguments.log.read_text())
    verify(report, cases, arguments.sha, arguments.run, program_hashes)
    print(json.dumps({"audit": "PASS", "verified_rows": len(EXPECTED)}))


if __name__ == "__main__":
    main()
