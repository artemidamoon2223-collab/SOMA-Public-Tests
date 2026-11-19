"""Domain-neutral candidate space. No fixture names, truth labels or phase inputs."""
from itertools import product

RULES = list(product(("inspect", "probe"), ("always", "unresolved", "different", "never")))


def investigate(rule, primary, initial_value, output, inspect, probe):
    plan = [rule[0], "probe" if rule[0] == "inspect" else "inspect"]
    sources = None
    verified = None
    eliminated = set()
    for index, action in enumerate(plan):
        if index == 1:
            allowed = {"always": True, "unresolved": verified is None,
                       "different": output != initial_value, "never": False}
            if not allowed[rule[1]]:
                break
        if action == "inspect":
            sources = inspect()
        else:
            target = sources[-1] if sources else primary
            response = probe(target)
            if response == "changed":
                verified = target
            elif response in ("absent", "unchanged"):
                eliminated.add(target)
        if sources:
            possible = [name for name in sources if name not in eliminated]
            if initial_value != output:
                possible = [name for name in possible if name != primary]
            if len(possible) == 1:
                verified = possible[0]
    return verified
