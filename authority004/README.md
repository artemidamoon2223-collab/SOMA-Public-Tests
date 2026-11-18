# CI-004 checkpoint authority experiment

## Frozen threat model

A local writer can replace its whole synthetic journal and its matching local anchor, and an intermediary can drop, delay or change checkpoint messages. The verifier holds a fresh one-use challenge and a retained generation/digest floor outside those mutable inputs. A simulated honest authority persists a unique ordered action log and accepts only writer-authenticated compare-and-append requests. It answers the challenge with its current generation and history digest. The two MAC domains use separate ephemeral fixture keys. MACs model trusted participants, including the verifier, which also holds the observation key.

We test freshness, conflicting authenticated observations for the same challenge, retained history, transactional unique action IDs, concurrent compare-and-append, and real process death on either side of commit. Read the local snapshot only while quiescent. One challenge belongs to one verification attempt. Challenge generation, key custody, independent storage of the floor, multi-host availability and power-loss durability are assumptions. All roles share one runner and Unix identity. The scope excludes a malicious authority, key compromise, direct rewriting of its database or the caller's floor. A common-domain rollback is a deliberate counterexample. Independent administrative security is NOT_VERIFIED.

A checkpoint is the length and SHA-256 of a canonical JSON array of unique synthetic action names. The digest of the local prefix at the retained generation must match the floor. The current snapshot must match both the local anchor and the challenge-bound authenticated response. A second authenticated observation at the same challenge must agree. A stale response fails freshness even if the verifier has no newer floor. A freshly authenticated regression below a retained floor fails monotonicity. Conflicts require both observations to reach the verifier. Silence cannot prove currency.

The sole frozen experiment runs on standard public Ubuntu. It uses only Python's standard library, temporary SQLite files and synthetic data. To reproduce from the repository root on Linux with Python 3.12:

```sh
timeout -k 3 60 python3 -I authority004/challenge.py > /tmp/ci004-report.json
python3 -I authority004/audit.py /tmp/ci004-report.json "$(git rev-parse HEAD)"
```

Use the tested commit in the execution receipt. Shell exit 0 is success. The verifier CLI returns 3 for a specified rejection. Unexpected subprocess failures cannot satisfy a rejection. No model calls or scientific evaluation.
