# CI-005 selective disclosure between two observers

## Question and assumptions fixed before execution

Two honest logical observers retain complete bounded views of one synthetic stream. Each may receive a different internally consistent sequence. A relay can suppress, delay, copy or alter their exchanged observations. Each observer can authenticate the two fixture identities and retains its own local evidence. The origin of the supplied histories, honest capture, freshness of round identifiers and integrity of retained local storage are assumptions. Both identities share one host and a trusted harness. A MAC in this fixture provides no third-party attribution.

A missing peer observation yields UNKNOWN. Seeing the same history establishes equality of the two disclosed views for that round. A proper prefix establishes compatibility up to the shorter length. Neither proves that no other hidden view exists. Two valid statements with different values at the same position provide a pairwise fork witness. Once recorded, that evidence should remain available after a process restart even if a later message is withheld. A previously unseen, shorter, compatible view alone cannot prove suppression.

The frozen schedule covers all 15 binary histories of lengths zero through three for each observer and all four directional delivery masks. This gives 900 schedules and 1,800 recipient decisions. A separate process-level trace checks asymmetric delivery, delayed exchange, restart, binding to the observer and round, altered attestations, and two indistinguishable hidden worlds. No real network or independent operator is involved. The local evidence store assumes serialized access by its one honest observer. The experiment does not model a malicious observer, host compromise or disk power loss.

From the repository root at the tested commit, run:

```sh
export SOURCE_SHA="$(git rev-parse HEAD)"
timeout -k 3 45 python3 -I -B views005/experiment.py > /tmp/views005.json
python3 -I -B views005/audit.py /tmp/views005.json "$SOURCE_SHA"
```

The receipt contains the actual matrix rows as zlib-compressed base64 TSV. Each row lists the left and right histories (a dash for empty), the delivery mask (bit 0 delivers to left, bit 1 to right), then each recipient's verdict and first conflicting one-based position (0 otherwise). The auditor constructs expected rows independently from the literal inputs. Verification never uses either expected histories or expected verdicts as protocol inputs.
