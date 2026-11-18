# CI-005 execution result

**RUNTIME_VERIFIED within the synthetic model.** One public Ubuntu 24.04 job, Python 3.12.3, attempt 1. Tested commit `5d8b5f7b62e7966f579574f795adb96b7f541f5c`. All steps succeeded. The 900 schedules produced 1,800 recipient decisions with zero mismatches against the independent literal-history oracle. The 13 process invocations matched their expected verdicts, positions, exit codes and retained evidence. The auditor rejected six deliberately changed reports. Those mutations are a separate count.

| Recipient decision | Observations |
|---|---:|
| UNKNOWN, no authenticated peer message received | 900 |
| EQUAL, the two disclosed histories matched | 60 |
| PREFIX, one disclosed history was a proper prefix | 272 |
| FORK, conflict at an identified position | 568 |

The left observer received byte-identical input in the hidden equal and hidden divergent worlds. It returned UNKNOWN in both. After one-way delivery the right observer identified a fork at position 3 while left still returned UNKNOWN. Delivering the peer statement to left enabled the same detection there. Fresh processes later loaded the original paired evidence, including the same proof-file digests, while new messages were withheld. The trace additionally covered a reflected statement, an altered history and a prior-round message.

Off-runner review compared the GitHub run and job to the candidate, read back all five frozen files, matched all 13 TRACE log lines to the report and checked its source digests. An auditor without protocol imports decompressed and checked every TSV row. Its six report-mutation controls also rejected off-runner. The test driver ran once in Actions. The run used read-only contents/metadata, no persistent checkout credentials and no caches or artifacts.

Independent operator security remains NOT_VERIFIED. EQUAL and PREFIX describe only the two disclosed views. A silent peer cannot distinguish accidental loss from deliberate withholding. The protocol assumes honest observation and protected retained state, uses a simulated relay and shares fixture MAC keys across one host. Restart here means new processes reading the retained evidence; power loss and filesystem rollback were outside scope.

[Actions run](https://github.com/artemidamoon2223-collab/SOMA-Public-Tests/actions/runs/44241832039) · [Job log](https://github.com/artemidamoon2223-collab/SOMA-Public-Tests/actions/runs/44241832039/job/134591327810) · [Machine receipt](EVIDENCE.json)

To check the saved runner output without re-executing the experiment, from this evidence checkout:

```sh
python3 -c 'import json; print(json.dumps(json.load(open("views005/EVIDENCE.json"))["report"]))' > /tmp/views005-saved.json
python3 -I -B views005/audit.py /tmp/views005-saved.json 5d8b5f7b62e7966f579574f795adb96b7f541f5c
```
