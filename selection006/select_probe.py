"""One-query policy over a disclosed pair of hypothetical observation models."""


def choose(models, policy):
    if policy == "fixed":
        return 0
    if policy != "separating":
        raise ValueError(policy)
    for index, (first, second) in enumerate(zip(*models)):
        if first != second:
            return index
    return 0  # Spend the identical budget even when no channel separates.


def conclude(models, index, observed):
    possible = [i for i, model in enumerate(models) if model[index] == observed]
    return possible[0] if len(possible) == 1 else None
