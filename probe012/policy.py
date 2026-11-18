"""Only disclosed configs, baseline stdout and a one-call observation function enter here."""
CANDIDATES = ("blue", "green", "defaults")
POLICIES = ("always_blue", "conditional_blue", "conditional_defaults", "select")


def prediction(config, override, edit=None):
    active = config["launch"]["profile"]
    order = [active, "defaults"] if override else ["defaults", active]
    for source in order:
        if source is None:
            continue
        if source == edit:
            return 91, source
        if "limit" in config[source]:
            return config[source]["limit"], source
    return None, None


def investigate(config, baseline, policy, probe):
    modes = [mode for mode in (False, True) if prediction(config, mode)[0] == baseline]
    original = {prediction(config, mode) for mode in modes}
    if len(original) == 1 and policy != "always_blue":
        return list(original.pop())
    if policy == "select":
        # Stable tie order favors profile files when a default edit is equally informative.
        target = max(CANDIDATES, key=lambda path: len({prediction(config, m, path)[0] for m in modes}))
    elif policy == "conditional_defaults":
        target = "defaults"
    else:
        target = "blue"
    observed = probe(target)
    remaining = {prediction(config, m) for m in modes if prediction(config, m, target)[0] == observed}
    return list(remaining.pop()) if len(remaining) == 1 else None
