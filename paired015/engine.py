"""Trusted, bounded fixture runner; policies receive only the observation callbacks."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zlib

from policy import investigate


def write(path, value):
    path.write_text(json.dumps(value))


def start(root):
    p = subprocess.run([sys.executable, "-I", "-B", "app.py"], cwd=root, text=True,
                       capture_output=True, timeout=3)
    if p.returncode or p.stderr:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def pack(rows):
    return base64.b64encode(zlib.compress(json.dumps(rows, separators=(",", ":")).encode(), 9)).decode()


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def run_case(root, domain, spec, rules):
    primary, secondary = domain.FILES
    source, documents = domain.build(spec)
    (root / "app.py").write_text(source)
    for name, doc in zip(domain.FILES, documents):
        write(root / name, doc)
    output = start(root)
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "oracle"
        shutil.copytree(root, clone)
        for i, name in enumerate(domain.FILES):
            domain.replace(clone / name, "oracle-" + str(i))
        tagged = start(clone)
    actions = []
    for rule in rules:
        trace = []
        permitted = {primary}
        def inspect():
            if len(trace) >= 2:
                raise ValueError("inspection budget")
            names = None
            if spec[-1] != "opaque":
                syntax = ast.parse((root / "app.py").read_text())
                names = [node.value for node in sorted(
                    (n for n in ast.walk(syntax) if isinstance(n, ast.Constant) and n.value in domain.FILES),
                    key=lambda n: (n.lineno, n.col_offset))]
                permitted.update(names)
            trace.append(["inspect", names])
            return names

        def probe(name):
            if len(trace) >= 2 or name not in permitted:
                raise ValueError("probe scope")
            if spec[-1] in ("opaque", "no_probes"):
                response = "unavailable"
            else:
                with tempfile.TemporaryDirectory() as tmp:
                    clone = Path(tmp) / "probe"
                    shutil.copytree(root, clone)
                    if domain.replace(clone / name, "probe-91"):
                        response = "changed" if start(clone) == "probe-91" else "unchanged"
                    else:
                        response = "absent"
            trace.append(["probe", name, response])
            return response
        answer = investigate(rule, primary, spec[0], output, inspect, probe)
        actions.append([trace, answer])
    return [spec, output, tagged, actions]
