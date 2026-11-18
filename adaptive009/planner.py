"""Select from all bounded plans using only the disclosed hypotheses."""
from itertools import product


def traverse(models, plan, observe):
    first, after_zero, after_one = plan
    viable = list(range(len(models)))
    trace = []
    channel = first
    for _ in range(2):
        answer = observe(channel)
        trace.append((channel, answer))
        viable = [h for h in viable if models[h][channel] == answer]
        if len(viable) <= 1:
            break
        channel = (after_zero, after_one)[answer]
    return trace, viable[0] if len(viable) == 1 else None


def best_plan(models, adaptive):
    candidates = []
    for first in range(3):
        remaining = sorted(set(range(3)) - {first})
        for zero, one in product(remaining, repeat=2):
            if not adaptive and zero != one:
                continue
            plan = (first, zero, one)
            projected = [traverse(models, plan, row.__getitem__) for row in models]
            resolved = sum(label is not None for _, label in projected)
            cost = sum(len(trace) for trace, _ in projected)
            candidates.append((-resolved, cost, plan))
    return min(candidates)[2]
