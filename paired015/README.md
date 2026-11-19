# CI-015 · When a default and an override look identical

Test the CI-014 frozen inspect/unresolved rule, with inspect/always as the paired comparison. Both policy.py and engine.py are verbatim public blobs from commit 68c3e9eaae48d428ea469466a9dc5014a2a7ce55. Each rule has the same two-check budget. There is no training step.

Eight pairs cross two strings, two ways to spell a path, and two probe-access modes. Both files store the same ordinary value. Within each pair, only the enabled flag in boot.json changes. The app source, visible output, and initial inspection are identical. A separate launch tags both files in a disposable copy to establish which file supplied the result. The open probe edits one file in another disposable copy. The restricted probe returns unavailable.

The claim requires the frozen rule to request a second observation in both members of every ambiguous pair and to make zero false attributions. Report abstentions separately. A complete audit may return claim_pass=false. This is a counterexample and must be preserved. The workflow exit status covers receipt integrity. The study tests a fixed policy paired with a literal-filename inspector. It uses public synthetic data and has no production or scientific validation role.

Reproduce at the tested source commit using Python 3.12 on Linux:

```sh
export SOURCE_SHA=$(git rev-parse HEAD)
python3 -I -B paired015/experiment.py > receipt.log
python3 -I -B paired015/audit.py receipt.log "$SOURCE_SHA"
```

The log stores both schedules, ordinary and tagged outputs, every requested check and its response. The auditor checks the 16-case matrix, checks the two schedules and observations, and challenges four corrupted receipts.
