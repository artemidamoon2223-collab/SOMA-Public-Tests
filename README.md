# SOMA public Linux engineering preflight

This repository contains **new, standalone public synthetic fixtures**. It does
not contain SOMA production code, private tests, datasets, evaluation answers or
keys. A passing run measures the runner and these fixtures only.

## Reproduce

On an ordinary, unprivileged Linux account with Python 3.12 and `unshare`:

```sh
timeout --signal=TERM --kill-after=5s 120s python3 -B tests/preflight.py --output results/preflight.json
python3 -B tests/verify_report.py results/preflight.json
```

Only the Python standard library is used. No packages, models or external
services are installed by the tests. They do not make network requests. Namespace
probes never retry with elevated privileges. A permission denial is `BLOCKED`;
an absent feature is `UNSUPPORTED`; unexpected behavior is `FAIL`.

The workflow uses the standard `ubuntu-24.04` GitHub-hosted runner, Python 3.12,
read-only `contents` permission, pinned official actions, one job and a six-minute
job timeout. The suite has a 120-second outer bound, per-child timeouts, at most
four concurrent worker processes, a 512 MiB address-space bound, an 8 MiB file
size bound and a 128-descriptor bound. Resource probes only lower their own
limits. No sudo, privileged containers, larger/self-hosted runners, cache,
artifact-storage upload, secrets or private checkout are configured.

Standard GitHub-hosted runner execution is free for public repositories:
https://docs.github.com/en/actions/concepts/billing-and-usage

## Evidence and interpretation

Each run prints `CASE_JSON`, `REPORT_JSON` and `VERIFICATION_JSON` records to the
Actions logs and writes a step summary. The handoff preserves the actual report,
run/job links and source commit in `evidence/`. Logs are provider-retained and may
expire; committed reports remain independently inspectable. No test result is
claimed merely because a workflow file exists.

The separate report verifier checks complete case membership, status counts,
source SHA-256 and critical measurements. Four deliberately altered reports must
be rejected. This is an independent code path, not an external security audit.

## Limits

- AF_UNIX peer credentials are tested between same-user processes. Cross-user
  authorization, hostile worker confinement and production isolation are not
  established.
- File modes, locks, atomic replacement and SQLite process-crash recovery do not
  prove power-loss or disk-failure durability.
- The synthetic journal is hash-linked and locally anchored, **not authenticated**.
  A writer able to replace both journal and anchor can forge or roll back them.
  No Owner key or HMAC/signing secret is used.
- UNKNOWN_OUTCOME blocks replay after the test has established worker death.
  This fixture is not a distributed lease or general exactly-once system.
- Namespace availability is measured without privilege escalation; blocked
  namespaces remain blocked. No root or production sandbox claim follows.
- These tests do not establish production SOMA correctness or cognitive gains.

SCIENTIFICALLY_VALIDATED=NO
CONFIRMATORY_SET_USED=FALSE
NEW_LIVE_MODEL_CALLS=0
