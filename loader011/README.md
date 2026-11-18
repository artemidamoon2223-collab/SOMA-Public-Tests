# Conditional inspection of loader code

Two synthetic applications share app.py and identical configuration files for each paired case. Their on-disk loader.py implements either defaults | profile (override) or profile | defaults (fill missing). The investigator knows both possible algorithms but receives no indicator of which one is active. It can request loader.py and match the actual syntax tree against the two allowed functions. This is a hand-authored investigation policy for a closed grammar.

The 36 worlds cover both loaders, profile enabled/disabled, and missing, zero or seven for each definition. The evaluator records the real application's stdout. It replaces each existing definition alone with 91, executes again, and restores the file to verify the causal source even when the two definitions have the same integer. If neither active input supplies the key, a supported pair of nulls describes the absent setting. A bare null decision means abstention.

Compare an eager policy that reads the implementation first and then uses the discovered precedence, and a conditional policy that first inspects configuration. Both stop when they can establish the full pair and have four distinct file requests, including failed reads. In a second condition the investigator cannot read loader.py. The application remains intact. An independent auditor enumerates consistent worlds, checks all observed reads, the value/source pair, the need for a loader request, and runtime interventions. It counts excess reads for successful conclusions by finding the smallest subset of that run's actual receipts that still proves the answer. This hindsight metric need not be attainable by an online policy.

Reproduction at the tested revision, from the repository root:

```sh
export SOURCE_SHA="$(git rev-parse HEAD)"
python3 -I -B loader011/experiment.py > /tmp/loader011.json
python3 -I -B loader011/audit.py /tmp/loader011.json "$SOURCE_SHA"
```
