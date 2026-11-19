# CI-016 · Preserve correct source attributions
The candidate is frozen before its single CI run. Gate on CI-015's 16 original cases: all four previously false answers must become correct or abstain, all eight correct answers must remain correct by case ID, and no new false answers may appear. Report every transition. Score 12 new cases separately and retain counterexamples.

The original-access rule reads the same filename inspection and probes one file. It accepts direct positive evidence only. In two original no-probe pairs with computed names the allowed observations coincide across the two source labels. Preserving the earlier lucky answer in both pairs while eliminating its false twin is impossible under those observations.

The additional-access rule requests one read-only provenance observation from a separate run of the cooperative app, even in cases where editing a file is prohibited. Path.read_text, JSON decoding, and the JSON output encoder carry and capture file identity for unmodified string values. The rule checks its captured output against the ordinary run. This requires instrumentation and is a different permission and cost from a file probe. The two rules have no access to the tagged oracle or enable flag. A missing witness, a lost label or an inconsistent output warrants abstention. A dishonest observer or malicious fixture is outside scope. The design supports the public fixtures' single direct print of a JSON string.

Three new loader patterns use a last-read decoy, a computed-path stack, and a string transformation that loses its label. A separate executable two-file tagging run provides the oracle. Original CI-015 baseline decisions come from the existing evidence file on the parent commit. Each case records the original-access trace, tagged output, new observer receipt and answer. Changes to the observer can change app semantics in general; this experiment checks ordinary output equality for each case.

Reproduce on Python 3.12 from the tested commit:

```sh
export SOURCE_SHA=$(git rev-parse HEAD)
python3 -I -B repair016/controls.py
python3 -I -B repair016/trial.py > receipt.log
python3 -I -B repair016/audit.py receipt.log paired015/EVIDENCE.json "$SOURCE_SHA"
```

Workflow success means the records passed the auditor. The per-method target_met fields report the engineering outcome.
