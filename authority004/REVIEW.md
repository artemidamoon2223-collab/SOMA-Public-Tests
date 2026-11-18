# CI-004 execution review

Frozen candidate `3e834a1cf545581f6fd340adedd8b536ed2179af`, off public main `4cc33643e9783adb9bfed53c251763d136373dd0`. One public Actions push run, attempt 1, one standard ubuntu-24.04 job, Python 3.12.3. The job completed in six seconds. All five steps succeeded. Logs show Contents and Metadata read permissions. Checkout was pinned and did not persist credentials. No external test services, cache, artifacts or private checkout.

[Run 44240008286](https://github.com/artemidamoon2223-collab/SOMA-Public-Tests/actions/runs/44240008286) · [Job log](https://github.com/artemidamoon2223-collab/SOMA-Public-Tests/actions/runs/44240008286/job/134585297223) · [Machine receipt](EVIDENCE.json)

**22/22 scenario outcomes matched, 0 failed.** Six deliberately damaged reports were separately rejected for their expected reasons. These totals describe one experiment. Independent off-runner review used the GitHub run and job records, decoded job log, the frozen oracle and direct readback of the five candidate files. Each of the 22 separately printed case rows matched the aggregate report exactly, including child exit code, stdout, stderr, SQLite integrity and ordered durable IDs. The run SHA matched the frozen commit, and all five file hashes matched reviewed bytes. Off-runner execution of the auditor against the downloaded report reproduced the totals and mutation rejections. The experimental scenario driver ran only once in Actions.

| Observation | Actual result |
|---|---|
| Unauthorised append | UNAUTHORIZED, exit 3, no new action |
| Two writers, one parent | beta committed; gamma returned PARENT_CHANGED, exit 3 |
| Stale authenticated message, newly authenticated regression, fork at the retained floor | STALE_CHALLENGE, BELOW_FLOOR, FLOOR_FORK respectively |
| Conflicting authenticated observations presented together | CONFLICT, exit 3 |
| Process killed before commit | Child -9 with empty output; newer action absent after reopening SQLite |
| Process killed after commit, before reply | Child -9 with empty output; newer action appeared exactly once. Old local snapshot rejected; recovered snapshot accepted. Reuse returned REUSED_ACTION |
| Rollback of the caller's floor together with authority and local state | ACCEPT, exit 0. This expected counterexample demonstrates the trust assumption |

For the counterexample and fork controls a second SQLite snapshot models the authority serving the alternative view with the same synthetic observation key. The harness queries the original primary database for each row's durable action list. Those rows record the reference primary. The verification subprocess receives the observation from the chosen snapshot. The conflicting-view control presents both at once. The experiment does not establish detection of withholding when the verifier sees only one consistent view.

**RUNTIME_VERIFIED** applies to the synthetic outcomes above. **SOURCE_VERIFIED** applies to the files at the frozen candidate. **NOT_VERIFIED** applies to real independent custody, private integration, power loss and scientific improvement. One runner/UID holds all roles and ephemeral test keys. The threat model trusts the caller to issue a unique challenge and to retain its floor; it also trusts the authority to retain and faithfully report its state. These are bounded fixtures, not a network service, a general parser fuzzer or a proof against a malicious runner.

Reproduce the report from the tested commit using the commands in README.md. At the evidence commit, audit the saved report with the original tested SHA as described below:

```sh
python3 -c 'import json; print(json.dumps(json.load(open("authority004/EVIDENCE.json"))["report"]))' > /tmp/ci004-saved.json
python3 -I authority004/audit.py /tmp/ci004-saved.json 3e834a1cf545581f6fd340adedd8b536ed2179af
```
