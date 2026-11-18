# Choosing a causal probe with a hidden configuration loader

The two possible loaders apply the selected profile over defaults or fill missing defaults from the profile. A hand-written investigator knows both hypotheses. Its inputs are the four disclosed JSON configurations, the original stdout and a callback allowing at most one additional process launch in a disposable copy. It receives neither loader source nor oracle output. These are logical interfaces within a trusted synthetic harness.

The 162 cases exhaust both loaders, three selections (off, blue, green), and three possibilities at each definition (absent, zero, seven). Each intervention sets one setting to the fresh integer 91, adding it if absent. The requested answer always concerns the original configuration and includes its value and source. An absent setting is a supported pair of nulls; an undecidable source requires abstention. The harness checks that exactly one clone file changed and the original snapshot is intact.

Four policies separate the benefit of skipping a probe from the benefit of choosing its target. One always changes blue. Two probe only on ambiguity and always change blue or defaults respectively. The selector simulates each permitted edit under the surviving hypotheses and selects the one with the most distinct predicted outputs. Ties prefer blue, green, then defaults. All arms use the same evidence-based final decision. The fixed-default arm tests whether a simple intervention can already solve every ambiguous case under these two precedence rules.

A separate oracle launches a tagged copy with a different marker for each existing definition, preserving key presence and profile selection. Its output identifies the winning source. The external auditor independently reconstructs original and post-edit outcomes, checks the oracle and each actual intervention, checks supported conclusions, and must reject three altered reports. Planning computation is unmetered; shared baseline and oracle launches are counted separately from policy probes. This is a bounded engineered comparison without learning or inference.

Reproduce from the repository root at the tested commit:

```sh
export SOURCE_SHA="$(git rev-parse HEAD)"
python3 -I -B probe012/experiment.py >/tmp/probe012.json
python3 -I -B probe012/audit.py /tmp/probe012.json "$SOURCE_SHA"
```
