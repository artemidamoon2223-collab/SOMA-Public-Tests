# CI-018 · Choose file interventions after a lost provenance label

Freeze both policies before running. Entry requires the actual CI-017 observer to produce the ordinary output and one unlabeled sink. Public hypotheses describe which editable value files can influence that output. Each policy receives that catalogue, allowed filenames and a callback returning a binary outcome; it receives no oracle, case identifier or app source. Every request launches the real synthetic app in a disposable copy with exactly one value changed. The independent oracle uses a different marker in each separate one-file trial across all files. Oracle edits are never offered to the policies.

Score exact sets of source files. After each observation discard incompatible hypotheses and stop on a singleton. The adaptive planner chooses the file minimizing the larger remaining partition, breaking ties by filename. The fixed comparator commits to the best ordered pair for the public catalogue (maximum identifiable hypotheses under equal weights, minimum total queries, lexical tie break). Both get at most two distinct allowed edits. Inspection, observer launches, planning CPU and evaluator-only trials are outside the edit budget.

Reuse precisely the six CI-017 abstention fixtures and compare output, label-loss observation and dependencies against the recorded evidence. Give both policies all four possible source subsets, including the empty set. Add 30 synthetic cases with four possible files and two filename rotations. They cover branching, early resolution, limited access and zero access. Within each group the ordinary output is identical. New loader catalogues are deliberately exhaustive for these fixtures. A unique answer depends on that assumption and on faithful intervention predictions. Restricted or denied edits leave unresolved cases open. No private source, model or protected evaluation is involved.

Predeclared target: recover all six earlier abstentions with exact source sets, show different second-file choices after opposite first responses in both rotations, exceed the best fixed order on the fork cohort, exercise correct early stops, and avoid false attributions including under access limits. A successful workflow establishes receipt integrity. Check target_met separately.

Reproduce from the tested commit on Ubuntu with Python 3.12:

```sh
export SOURCE_SHA=$(git rev-parse HEAD)
python3 -I -B probes018/run.py > receipt.log
python3 -I -B probes018/audit.py receipt.log trim017/EVIDENCE.json "$SOURCE_SHA"
```
