# CI-019 · Missing hypotheses

Test the published CI-018 adaptive planner unchanged. Freeze both the matrix and the scoring code before one public Ubuntu run. The safety claim under test is zero incorrect exact-source answers when the truth may be absent. A successful workflow validates receipts independently of whether the claim survives.

Enumerate all eight source subsets of three public JSON files, including a constant-output fixture. Cross this with a catalogue containing {a}, {b}, {a,b}, or the catalogue of all seven nonempty subsets, and with access to all files or only a. This yields 32 cases. None of the apps or previous CI suites is used as a benchmark for private SOMA. Before deciding, each fixture must have the same ordinary output and no provenance label. Only the catalogue, permitted filenames and binary one-file intervention outcomes reach the frozen planner. The budget is two distinct file edits in disposable copies. Record answers and abstentions for listed and omitted truths separately. A contradiction requires that zero listed hypotheses fit the observed trace; abstention can also mean multiple listed possibilities remain.

After the decision, an external control probes c on each of the eight open cases whose catalogue never mentions c. This observation is withheld from the planner and excluded from its accounting. The evaluator independently changes each file with a different marker and checks its output against the fixture declaration. For each incorrect attribution require an actually executed listed twin with identical ordinary output, lost-label witness, requested files, raw probe responses and returned answer. These counts describe exhaustive synthetic cases within this design, not a population error rate.

Reproduce from the tested commit using Python 3.12:

```sh
export SOURCE_SHA=$(git rev-parse HEAD)
python3 -I -B open019/trial.py > receipt.log
python3 -I -B open019/audit.py receipt.log "$SOURCE_SHA"
```
