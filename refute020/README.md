# CI-020 · Attempt to refute the last listed hypothesis

Stacked on CI-019. Reuse its unchanged fixture builder, intervention callback and frozen adaptive selector. The selector receives the same catalogue and permitted filenames and runs first. A singleton is provisional. If a permitted second probe remains, challenge it, prioritizing files absent from all listed alternatives, then predicted contributors, then lexical order. Track observed contributors and untested files. An exact set requires evidence for every file in the declared input inventory; an empty proved set and an abstention are distinct outcomes.

Freeze case matching, the challenge rule and the two-probe cap before executing. Score each of the nine old errors, five old correct answers and eighteen abstentions separately. Count direct refutations separately from abstention due to unresolved alternatives. Require a second executed truth assignment with the same permitted interface and full trace for every historical abstention. These fixtures allow unrestricted subsets: when three input files are possible, two binary one-file edits leave at least one membership bit unresolved. Four separate two-file controls cover every subset, including empty and both, so the protocol can distinguish supported answers from blanket abstention.

The inventory and reproducible binary interventions are trusted for these cooperative public fixtures. The oracle edits use another marker after decisions. Probe budget excludes baseline, label check, and evaluator-only runs. A green workflow indicates receipt integrity; numerical attribution outcomes are in the audit.

Reproduce from the tested commit on Ubuntu with Python 3.12:

```sh
export SOURCE_SHA=$(git rev-parse HEAD)
python3 -I -B refute020/trial020.py > receipt.log
python3 -I -B refute020/audit.py receipt.log open019/EVIDENCE.json "$SOURCE_SHA"
```
