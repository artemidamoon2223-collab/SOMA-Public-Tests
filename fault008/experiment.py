import base64
import itertools
import json
import os
from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from policy import decide

POLICIES = ("first_difference", "fixed_robust", "difference_robust")


def trial(models, actual, policy):
    observations = []
    trace = ""
    for _ in range(4):
        action, value = decide(models, tuple(observations), policy)
        if action == "answer":
            return trace + "=" + str(value)
        if action == "abstain":
            return trace + "=?"
        if action != "query" or len(observations) >= 3 or value in dict(observations):
            raise RuntimeError("invalid request")
        bit = actual[value]
        observations.append((value, bit))
        trace += str(value) + str(bit)
    raise RuntimeError("budget exceeded")


def main():
    words = list(itertools.product((0, 1), repeat=4))
    lines = []
    for models in itertools.product(words, repeat=2):
        for truth, faulty_channel in itertools.product(range(2), range(-1, 4)):
            actual = list(models[truth])
            if faulty_channel >= 0:
                actual[faulty_channel] ^= 1
            lines.append(",".join(trial(models, actual, p) for p in POLICIES))
    # Deliberately violate the one-error assumption in an isolated boundary control.
    boundary = trial((words[0], words[-1]), (1, 1, 0, 0), "difference_robust")
    data = zlib.compress("\n".join(lines).encode(), 9)
    print(json.dumps(dict(commit=os.environ["SOURCE_SHA"], traces=base64.b64encode(data).decode(),
                          two_error_truth_zero=boundary), separators=(",", ":")))


if __name__ == "__main__":
    main()
