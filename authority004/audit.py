"""Independent public oracle. Does not import the authority or the challenge driver."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
FILES = {"authority004/protocol.py", "authority004/challenge.py", "authority004/audit.py",
         "authority004/README.md", ".github/workflows/soma-checkpoint-004.yml"}
ORACLE = [
    ("writer_grant", "APPENDED"), ("wrong_writer", "UNAUTHORIZED"),
    ("concurrent_parent", "RACE"), ("current", "ACCEPT"),
    ("rollback_pair", "AUTHORITY_MISMATCH"), ("replacement_pair", "AUTHORITY_MISMATCH"),
    ("authenticated_stale", "STALE_CHALLENGE"), ("lost_anchor_write", "LOCAL_ANCHOR"),
    ("missing", "MISSING_OBSERVATION"), ("malformed", "MALFORMED_OBSERVATION"),
    ("altered_mac", "BAD_OBSERVATION_MAC"), ("fresh_below_floor", "BELOW_FLOOR"),
    ("common_domain_counterexample", "ACCEPT"), ("conflicting_observations", "CONFLICT"),
    ("fork_at_floor", "FLOOR_FORK"), ("killed_before_commit", "KILL"),
    ("restart_before_commit", "ACCEPT"), ("killed_after_commit", "KILL"),
    ("incomplete_local_recovery", "AUTHORITY_MISMATCH"),
    ("restart_after_commit", "ACCEPT"), ("reused_identity", "REUSED_ACTION"),
    ("truncated_envelope", "MALFORMED_ENVELOPE"),
]


def require(value, field):
    if not value:
        raise ValueError(field)


def audit(doc, sha):
    require(set(doc) == {"schema", "commit", "files", "cases", "authority_independence"}, "schema keys")
    require(type(doc["schema"]) is int and doc["schema"] == 1, "schema version")
    require(re.fullmatch(r"[0-9a-f]{40}", sha) and doc["commit"] == sha, "commit")
    require(doc["authority_independence"] == "NOT_VERIFIED", "trust classification")
    require(doc["files"] == {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES},
            "source hashes")
    require(len(doc["cases"]) == len(ORACLE), "case count")
    durable = ["alpha"]
    for row, (name, verdict) in zip(doc["cases"], ORACLE):
        require(set(row) == {"name", "sqlite", "calls", "durable_actions"}, "row schema")
        require(row["name"] == name and row["sqlite"] == "ok", "case identity or integrity")
        calls = row["calls"]
        require(all(isinstance(call, list) and len(call) == 3 and type(call[0]) is int
                    for call in calls), "call schema")
        if verdict == "RACE":
            ok, loser = [0, "APPENDED", ""], [3, "PARENT_CHANGED", ""]
            require(calls in ([ok, loser], [loser, ok]), name)
            durable.append("beta" if calls[0] == ok else "gamma")
        elif verdict == "KILL":
            require(calls == [[-9, "", ""]], name)
            if name == "killed_after_commit":
                durable.append("later")
        else:
            code = 0 if verdict in {"APPENDED", "ACCEPT"} else 3
            require(calls == [[code, verdict, ""]], name)
        require(row["durable_actions"] == durable, "durable history: " + name)


def controls(doc, sha):
    changes = [
        ("omission", "case count", lambda d: d["cases"].pop()),
        ("fake pass", "authenticated_stale", lambda d: d["cases"][6].update(calls=[[0, "ACCEPT", ""]])),
        ("wrong crash", "killed_before_commit", lambda d: d["cases"][15].update(calls=[[1, "", ""]])),
        ("lost commit", "durable history: killed_after_commit",
         lambda d: d["cases"][17]["durable_actions"].pop()),
        ("source substitution", "source hashes", lambda d: d["files"].update({"authority004/audit.py": "0"*64})),
        ("unearned trust", "trust classification", lambda d: d.update(authority_independence="VERIFIED")),
    ]
    rejected = []
    for label, reason, change in changes:
        broken = copy.deepcopy(doc)
        change(broken)
        try:
            audit(broken, sha)
        except ValueError as error:
            require(str(error) == reason, "mutation rejected for wrong reason")
            rejected.append(label)
        else:
            raise ValueError("auditor accepted " + label)
    return rejected


if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text())
    audit(data, sys.argv[2])
    rejected = controls(data, sys.argv[2])
    print("AUDIT " + json.dumps({"cases_pass": len(ORACLE), "cases_fail": 0,
                                 "corrupt_reports_rejected": rejected}, separators=(",", ":")))
