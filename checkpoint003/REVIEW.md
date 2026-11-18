# Public-first engineering review

## Repository and integration order

The public repository contains standalone fixtures and reproducible synthetic
tests. Use the standard public Ubuntu runner after checking the runner label and
current billing policy. Keep fixture input, dependencies, logs and stored
evidence suitable for public disclosure. Pin the tested commit and confirm the
run SHA, job result, exact outcomes and source hashes. Keep failed evidence.
Production integration and scientific evaluations require separate review.

| Public draft | Base | Verified head | Existing runtime evidence |
|---|---|---|---|
| [CI-001](https://github.com/artemidamoon2223-collab/SOMA-Public-Tests/pull/1) | main | `a46fb73abd09e1262e0487e2c1e143ad9212e300` | 13 PASS and 1 BLOCKED in each recorded run |
| [CI-002](https://github.com/artemidamoon2223-collab/SOMA-Public-Tests/pull/2) | ci/public-linux-preflight-001 | `17d720da5f723cd88616aea0de5a0c967621c90e` | Four repetitions, 80 PASS and 0 FAIL |
| Checkpoint verifier | main | Candidate `3fab9605d6567c34911fd9a2dc8e81d05a56011d` | One new run, 12 PASS and 0 FAIL |

Review CI-001 first. After explicit Owner approval and its eventual merge,
verify CI-001 is present in main. Then check CI-002's base and its effective
diff against main. If needed, retarget CI-002 only with explicit approval after
confirming the diff contains its own changes. A squash can change ancestry and
require a clean review branch. Keep the CI-001 branch until the stack is
resolved. Review and obtain separate approval for any later CI-002 merge.
The standalone checkpoint draft can be reviewed independently.

## Checkpoint result

SOURCE_VERIFIED: the frozen public candidate was read back against the authored
files. GitHub Actions ran on standard `ubuntu-24.04`, one three-minute job, a
45-second test deadline and process memory, descriptor and file-size limits.
The read-only permissions are recorded in the actual job log. Cost basis:
[GitHub public runner policy](https://docs.github.com/en/actions/reference/runners/github-hosted-runners#standard-github-hosted-runners-for-public-repositories)
and [GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
The workflow uses no external paid service or storage uploads.

RUNTIME_VERIFIED: [run 44233997442](https://github.com/artemidamoon2223-collab/SOMA-Public-Tests/actions/runs/44233997442)
and [job 134565599263](https://github.com/artemidamoon2223-collab/SOMA-Public-Tests/actions/runs/44233997442/job/134565599263)
ran the exact frozen candidate. Two positive and ten rejection cases passed.
The coordinated rollback matched its stale local anchor and was rejected against
the separately supplied trusted checkpoint. The distinct same-generation
history and an unconfirmed newer history were also rejected. The real SIGKILL
between journal replacement and updating its local anchor yielded exit -9 in
the crash fixture and LOCAL_MISMATCH in the verifier. All checked files stayed
unchanged during the verification. No completed experiment was repeated.

The separate auditor checked recorded reasons, exact process exit codes,
unchanged state and program hashes. It rejected four altered reports. The
structured result is in [EVIDENCE.json](EVIDENCE.json). To review a downloaded
job log on this branch:

```sh
python3 -I checkpoint003/audit_report.py JOB_LOG --sha 3fab9605d6567c34911fd9a2dc8e81d05a56011d --run 44233997442
```

BLOCKED: previously observed mount namespace restriction remains documented.
NOT_VERIFIED: different Unix identities, hostile-process isolation, persistence
or authentication of the checkpoint authority, power-loss recovery, real
implementation integration and scientific outcomes.

SCIENTIFICALLY_VALIDATED=NO  
CONFIRMATORY_SET_USED=FALSE  
NEW_LIVE_MODEL_CALLS=0
