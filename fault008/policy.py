"""Deterministic public policies. A row is a hypothesis's four predictions."""


def decide(models, observations, policy):
    allowance = 0 if policy == "first_difference" else 1
    feasible = []
    for index, model in enumerate(models):
        mismatches = sum(model[channel] != value for channel, value in observations)
        if mismatches <= allowance:
            feasible.append(index)
    if len(feasible) == 1:
        return "answer", feasible[0]
    if not feasible or len(observations) >= 3:
        return "abstain", None
    used = {channel for channel, _ in observations}
    available = [channel for channel in range(4) if channel not in used]
    if policy != "fixed_robust":
        differences = [channel for channel in available if models[0][channel] != models[1][channel]]
        if differences:
            return "query", differences[0]
    return "query", available[0]
