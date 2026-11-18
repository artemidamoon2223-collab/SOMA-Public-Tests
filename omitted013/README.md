# Investigation with an omitted configuration source

Each investigator receives two known JSON settings and baseline stdout. Its initial explanations are default-wins and profile-wins. The application can additionally load a saved value at a filename found in its loader. A wrong attribution counts as wrong even when the number matches stdout.

The 40 equally enumerated cases cross two precedence rules, two values (0, 7) in each known file, and five saved-state conditions: unused decoy, referenced empty file, or a referenced value of 0, 7 or 11. Some saved values contradict both predictions, while others match a known value. A tagged oracle copy replaces each existing definition with a unique marker while preserving key presence. A separate process identifies the winning original source.

Each arm gets two additional checks at most. Reading the loader costs one. Trying to change one existing setting to 91 in a temporary copy costs one, even if its key is absent. An existing key triggers an actual process start. A new filename can be probed only after its literal occurs in the inspected code. The witness returns only the resulting number or the absence of a key. No arm receives the oracle result. These access rules are enforced by a trusted test callback on one host.

The closed policy accepts a single matching explanation, using a default probe to break ties. Contradiction-triggered inspection uses that same rule when baseline stdout fits an initial hypothesis; otherwise it inspects the loader and probes its highest-priority dependency. Two additional controls directly test matching known files until one changes stdout, or always inspect and probe the discovered dependency. All policy logic is hand-authored. The inspection parser supports the fixture's small grammar of merged dictionaries. The source filenames and tagged truth are never supplied as initial hypotheses about the third cause.

Reproduce from the repository root at the tested commit:

```sh
export SOURCE_SHA="$(git rev-parse HEAD)"
python3 -I -B omitted013/experiment.py > /tmp/omitted013.json
python3 -I -B omitted013/audit.py /tmp/omitted013.json "$SOURCE_SHA"
```

The receipt includes compressed rows with every actual loader read, intervention response, original output, oracle marker and final attribution. The auditor derives expected observations separately and rejects three modified receipts.
