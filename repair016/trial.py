import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "paired015")]
import engine
import experiment as legacy
import rule


class New:
    FILES = ("theme.json", "session.json")
    replace = staticmethod(legacy.replace)

    @staticmethod
    def build(spec):
        value, style, active, _ = spec
        prefix = """import json
from pathlib import Path
def read(path):
    return json.loads(Path(path).read_text())
"""
        if style == "late_decoy":
            body = """override = read("session.json")
fallback = read("theme.json")
selected = override if override["enabled"] else fallback
_ = fallback["value"]
print(json.dumps(selected["value"]))
"""
        else:
            body = """fallback = read("theme.json")
override = read(".".join(("session", "json")))
layers = [fallback] + ([override] if override["enabled"] else [])
value = layers[-1]["value"]
"""
            body += 'print(json.dumps(value.strip()))\n' if style == "transform" else 'print(json.dumps(value))\n'
        return prefix + body, [{"value": value}, {"value": value, "enabled": active}]


def main():
    print("COMMIT", os.environ["SOURCE_SHA"], flush=True)
    for domain, values, styles in [(legacy, ("amber", "teal"), ("literal", "computed")),
                                   (New, ("mint",), ("late_decoy", "stack", "transform"))]:
        for spec in itertools.product(values, styles, (False, True), ("open", "no_probes")):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                with patch.object(engine, "investigate", rule.original_access):
                    row = engine.run_case(root, domain, spec, [("inspect", "unresolved")])
                completed = subprocess.run([sys.executable, "-I", "-B", str(HERE / "observer.py")],
                                           cwd=root, timeout=4, text=True, capture_output=True, check=True)
                if completed.stderr:
                    raise RuntimeError(completed.stderr)
                observation = json.loads(completed.stdout)
                answer = rule.witnessed(row[1], observation)
                print("CASE", json.dumps([*row, observation, answer]), flush=True)


if __name__ == "__main__":
    main()
