"""Public hypotheses predict which individual file edits change output."""
from itertools import permutations


def keep(family, name, changed):
    return [h for h in family if (name in h) == changed]


def fixed_order(family, files):
    def rank(order):
        solved = cost = 0
        for model in family:
            possible = family
            for name in order:
                if len(possible) <= 1:
                    break
                possible = keep(possible, name, name in model)
                cost += 1
            solved += len(possible) == 1
        return -solved, cost, order
    return min(permutations(sorted(files), min(2, len(files))), key=rank)


def investigate(family, files, probe, adaptive):
    order = None if adaptive else fixed_order(family, files)
    possible = list(family)
    unused = set(files)
    for step in range(min(2, len(unused))):
        if len(possible) <= 1:
            break
        if adaptive:
            def rank(name):
                yes = sum(name in h for h in possible)
                return max(yes, len(possible) - yes), name
            name = min(unused, key=rank)
            if rank(name)[0] == len(possible):
                break
        else:
            name = order[step]
        unused.remove(name)
        changed = probe(name)
        possible = keep(possible, name, changed)
    return sorted(possible[0]) if len(possible) == 1 else None
