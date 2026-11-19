"""Standalone scoring and exact historical case matching, without running any fixture."""
import itertools
import json
from pathlib import Path
import sys

HISTORICAL = "86cec41cc6d81b1550d983dbf6475a76600cf642"


def require(test, reason):
    if not test:
        raise ValueError(reason)


def score(lines, history, commit):
    require(lines[0] == "COMMIT " + commit, "source binding")
    require(history["tested_commit"] == HISTORICAL, "historical source")
    old = {}
    for line in history["records"][1:]:
        spec, value, oracle, decisions = json.loads(line.removeprefix("CASE "))
        old[tuple(spec)] = (value, oracle, decisions[0])
    new = set(itertools.product(("mint",), ("late_decoy", "stack", "transform"),
                                (False, True), ("open", "no_probes")))
    require(len(old) == 16, "historical coverage")
    seen = set()
    totals = {}
    transitions = {}
    for line in lines[1:]:
        require(line.startswith("CASE "), "record framing")
        spec, output, tagged, decisions, observation, extended = json.loads(line[5:])
        key = tuple(spec)
        require(key not in seen and (key in old or key in new), "case membership")
        seen.add(key)
        value, style, enabled, access = spec
        historical = key in old
        names = ("defaults.json", "boot.json") if historical else ("theme.json", "session.json")
        require(type(enabled) is bool and output == value and tagged == f"oracle-{int(enabled)}", "tagged outcome")
        truth = names[int(enabled)]
        require(len(decisions) == 1, "decision count")
        trace, strict = decisions[0]
        require(len(trace) == 2 and trace[0][0] == "inspect", "original access budget")
        if historical:
            old_output, old_oracle, (old_trace, old_answer) = old[key]
            require((output, tagged, trace[0]) == (old_output, old_oracle, old_trace[0]), "historical observations")
        else:
            visible = list(reversed(names)) if style == "late_decoy" else [names[0]]
            require(trace[0] == ["inspect", visible], "new observations")
        target = trace[0][1][-1]
        response = "unavailable" if access == "no_probes" else "changed" if target == truth else "unchanged"
        require(trace[1] == ["probe", target, response], "probe receipt")
        require(strict == (target if response == "changed" else None), "strict decision")
        expected_origin = None if style == "transform" else truth
        require(observation == {"stdout": json.dumps(output) + "\n", "sinks": [[expected_origin, value]]},
                "observed provenance")
        require(extended == expected_origin, "witness decision")
        for method, answer in (("original_access", strict), ("witness_access", extended)):
            group = ("old" if historical else "new") + "/" + method
            result = "abstain" if answer is None else "correct" if answer == truth else "wrong"
            totals.setdefault(group, dict(correct=0, wrong=0, abstain=0))[result] += 1
            if historical:
                previous = "abstain" if old_answer is None else "correct" if old_answer == truth else "wrong"
                bucket = transitions.setdefault(method, {}).setdefault(previous, dict(correct=0, wrong=0, abstain=0))
                bucket[result] += 1
    require(seen == old.keys() | new, "incomplete coverage")
    return {"totals": totals, "historical_transitions": transitions,
            "target_met": {method: rows["correct"]["correct"] == 8 and
                           sum(rows["wrong"].values()) == 4 and totals["old/" + method]["wrong"] == 0
                           for method, rows in transitions.items()}}


if __name__ == "__main__":
    print("AUDIT", json.dumps(score(Path(sys.argv[1]).read_text().splitlines(),
          json.loads(Path(sys.argv[2]).read_text()), sys.argv[3]), sort_keys=True))
