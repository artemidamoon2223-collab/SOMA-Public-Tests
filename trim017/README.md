# CI-017 · Attribution through whitespace trimming

Freeze the observer before one bounded run. Count a historical success only when the same CI-016 case retains its correct source. The gate requires all 24 retained, all four former abstentions resolved, and zero incorrect answers. The 28 original fixtures come from the unmodified parent. Re-evaluate only the new observer and compare ordinary outputs and recorded oracle labels with the parent receipts.

The only added operation is argument-free str.strip on a labeled value. Use the normal Python result and preserve its file of origin. Calls with a character set and unsupported string operations return untagged strings. The CI-016 decision rule is unchanged. This remains a read-only observation of cooperative test programs.

The 12 new fixtures swap file roles in six pairs. Require six correct single-source answers for Unicode whitespace, all-whitespace input and chained trims. Require abstention on all four two-file cases and both unsupported uppercase cases. Two one-file interventions per new case check input sensitivity. Those interventions are evaluator-only, and both files are restored before measuring the observer. The claim concerns the value's data origin for these inputs; conditional control dependencies, arbitrary Python code and hostile instrumentation are outside scope.

Reproduce on Linux with Python 3.12 at the tested commit:

```sh
export SOURCE_SHA=$(git rev-parse HEAD)
python3 -I -B trim017/trial.py > receipt.log
python3 -I -B trim017/audit.py receipt.log repair016/EVIDENCE.json "$SOURCE_SHA"
```

A successful workflow indicates valid receipts. The audit's target_met field records whether the candidate met the frozen gate.
