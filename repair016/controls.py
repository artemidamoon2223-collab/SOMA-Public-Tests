"""Negative controls for missing and inconsistent runtime observations."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rule import witnessed

samples = [
    (None, None),
    ({"stdout": '"blue"\n', "sinks": [["file", "red"]]}, None),
    ({"stdout": '"red"\n', "sinks": [["file", "blue"]]}, None),
    ({"stdout": '"red"\n', "sinks": [[None, "red"]]}, None),
    ({"stdout": '"red"\n', "sinks": [["a", "red"], ["b", "red"]]}, None),
    ({"stdout": '"red"\n', "sinks": [["file", "red"]]}, "file"),
]
for observation, expected in samples:
    if witnessed("red", observation) != expected:
        raise ValueError("observation control failed")
print("CONTROLS 5 rejected, 1 accepted")
