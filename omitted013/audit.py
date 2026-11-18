"""Independent audit of source attribution, allowed observations, and probe costs."""
import base64
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import sys
import zlib


def require(ok, message):
    if not ok:
        raise ValueError(message)


def audit(rows):
    require(len(rows) == 40, "coverage")
    totals = defaultdict(Counter)
    for i, (baseline, tag, arms) in enumerate(rows):
        state = i % 5
        saved = ["session.json", "snapshot.json"][i % 2]
        names = ["defaults.json", "profile.json", saved]
        values = [7 * ((i // 10) % 2), 7 * ((i // 5) % 2), [11, None, 0, 7, 11][state]]
        order = [0, 1] if i < 20 else [1, 0]
        source_order = order + ([2] if state else [])
        winner = 2 if state >= 2 else order[-1]
        require(tag == 81 + winner and baseline == values[winner], "oracle")
        matches = [p for p in (0, 1) if values[p] == baseline]
        group = "ordinary" if winner != 2 else "coincident" if matches else "contradiction"
        require(len(arms) == 4, "arm coverage")
        for arm, (decision, trace) in zip(("closed","expand_on_contradiction","verify_known","inspect_first"), arms):
            require(len(trace) <= 2, "budget")
            stats = totals[arm + "/" + group]
            obs = []
            for event in trace:
                if event[0] == "read":
                    correct_source = "settings = " + " | ".join("read('%s')" % names[k] for k in source_order) + "\n"
                    require(event == ["read", correct_source], "source read")
                    obs.append("read")
                else:
                    _, path, value = event
                    k = names.index(path)
                    require(k < 2 or ("read" in obs and k in source_order), "undiscovered source")
                    expected = "no_key" if values[k] is None else 91 if k == winner else baseline
                    require(event == ["probe", path, expected], "intervention")
                    obs.append(k)
                    if value != "no_key":
                        stats["probe_starts"] += 1
            expand = arm == "inspect_first" or (arm == "expand_on_contradiction" and not matches)
            if expand:
                expected_ops = ["read", source_order[-1]]
                expected_decision = names[winner]
            elif arm == "verify_known":
                expected_ops = matches[:matches.index(winner)+1] if winner in matches else matches
                expected_decision = names[winner] if winner in matches else None
            else:
                expected_ops = [0] if len(matches) == 2 else []
                if len(matches) == 2:
                    expected_decision = names[0 if winner == 0 else 1]
                else:
                    expected_decision = names[matches[0]] if matches else None
            require(obs == expected_ops and decision == expected_decision, "policy trace")
            stats["checks"] += len(obs)
            stats["abstain" if decision is None else "correct" if decision == names[winner] else "wrong"] += 1
    return dict(groups=totals, application_starts=80 + sum(s["probe_starts"] for s in totals.values()))


if __name__ == "__main__":
    report = json.loads(Path(sys.argv[1]).read_bytes())
    require(report["sha"] == sys.argv[2], "commit")
    rows = json.loads(zlib.decompress(base64.b64decode(report["rows"], validate=True)))
    summary = audit(rows)
    for reason in ("oracle", "intervention", "policy trace"):
        bad = copy.deepcopy(rows)
        if reason == "oracle":
            bad[0][1] = 999
        elif reason == "intervention":
            bad[0][2][0][1][0][2] = 999
        else:
            bad[0][2][3][0] = "defaults.json"
        try:
            audit(bad)
        except ValueError as exc:
            require(str(exc) == reason, "incorrect mutation rejection")
        else:
            raise ValueError("accepted altered report")
    print("AUDIT " + json.dumps(summary))
