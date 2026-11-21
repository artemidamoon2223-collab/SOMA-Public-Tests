"""Run only the new candidate; past answers are read separately by the audit."""
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "repair016"))
import trial as prior
from rule import witnessed

NAMES = ["left.json", "right.json"]
EXPRESSIONS = {
    "unicode": "value.strip()",
    "blank": "value.strip()",
    "twice": "value.strip().strip()",
    "two_files": "value.strip(other)",
    "join": "(value + other).strip()",
    "upper": "value.strip().upper()",
}


def execute(root, script):
    run = subprocess.run([sys.executable, "-I", "-B", str(script)], cwd=root,
                         text=True, capture_output=True, timeout=4, check=True)
    if run.stderr:
        raise ValueError(run.stderr)
    return json.loads(run.stdout)


def write(root, files, docs, source):
    (root / "app.py").write_text(source)
    for name, doc in zip(files, docs, strict=True):
        (root / name).write_text(json.dumps(doc))


def measure(root, key, oracle):
    ordinary = execute(root, "app.py")
    observed = execute(root, HERE / "observe_trim.py")
    print("CASE", json.dumps([key, ordinary, observed, witnessed(ordinary, observed), oracle]), flush=True)


def historical():
    for domain, values, styles in [(prior.legacy, ("amber", "teal"), ("literal", "computed")),
                                   (prior.New, ("mint",), ("late_decoy", "stack", "transform"))]:
        for spec in itertools.product(values, styles, (False, True), ("open", "no_probes")):
            source, docs = domain.build(spec)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write(root, domain.FILES, docs, source)
                measure(root, spec, None)


def fresh():
    for style, reverse in itertools.product(EXPRESSIONS, (False, True)):
        names = list(reversed(NAMES)) if reverse else NAMES
        primary = {"unicode": "\u2003cedar\u00a0", "blank": " \t", "two_files": "!cedar!"}.get(style, " cedar ")
        source = ("import json\nfrom pathlib import Path\n"
                  "def read(p): return json.loads(Path(p).read_text())['value']\n"
                  f"value = read({names[0]!r})\nother = read({names[1]!r})\n"
                  f"print(json.dumps({EXPRESSIONS[style]}))\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = [{"value": primary}, {"value": "!"}]
            write(root, names, docs, source)
            changed = {}
            # Evaluator-only one-at-a-time interventions; restore before observation.
            for name, original, marker in zip(names, docs, (" moss ", "#"), strict=True):
                path = root / name
                path.write_text(json.dumps({"value": marker}))
                changed[name] = execute(root, "app.py")
                path.write_text(json.dumps(original))
            measure(root, [style, reverse], changed)


if __name__ == "__main__":
    print("COMMIT", os.environ["SOURCE_SHA"], flush=True)
    historical()
    fresh()
