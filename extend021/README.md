# CI-021 · Request one missing observation

This two-stage synthetic experiment continues all 36 CI-020 case receipts. Each decision starts from the original inventory and actual probe results only. The evaluator keeps the truth separately. No CI-020 suite is repeated.

First report positive, negative and untested file effects in the recorded synthetic environment. Request one specific untested file, breaking equal-information ties by filename. If all files have been checked, return the exact set and issue no request. Then evaluate the same prepared request in two branches. Allow at most one new edit of the named file in a disposable copy when permission is simulated; denial must result in zero edits and an identical partial report. Every final statement must agree with the independent CI-020 intervention oracle. Budget, inventory and the independent file-effect assumption are specific to the fixtures.

The 16 open cases start after two probes, the 16 one-file cases start after one, and four controls are already complete. In the one-file cases an allowance explicitly adds one named synthetic permission. It leaves a third file unknown. This evaluates decision behavior with an honest test broker. It supplies no production capability, authenticated external grant or real isolation claim.

The audit checks both branches, exact set vs partial evidence, and four corrupted receipts. Reproduce on Python 3.12 from the tested commit:

```sh
export SOURCE_SHA=$(git rev-parse HEAD)
python3 -I -B extend021/trial021.py > receipt.log
python3 -I -B extend021/audit.py receipt.log refute020/EVIDENCE.json "$SOURCE_SHA"
```
