import base64
import itertools
import json
import os
from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from planner import best_plan, traverse

words = list(itertools.product((0, 1), repeat=3))
records = []
for models in itertools.combinations(words, 4):
    plans = [best_plan(models, adaptive) for adaptive in (False, True)]
    for truth, word in enumerate(models):
        for plan in plans:
            reads = []
            def observe(channel):
                if channel in reads or len(reads) == 2:
                    raise ValueError("query budget")
                reads.append(channel)
                return word[channel]
            trace, conclusion = traverse(models, plan, observe)
            records.append([plan, trace, conclusion])
raw = json.dumps(records, separators=(",", ":")).encode()
print(json.dumps(dict(commit=os.environ["SOURCE_SHA"],
                      traces=base64.b64encode(zlib.compress(raw, 9)).decode())))
