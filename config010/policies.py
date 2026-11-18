"""Each policy sees only the files returned by the bounded reader."""
DEFAULT = "defaults.json"
LAUNCH = "launch.json"


def supported(seen):
    launch = seen.get(LAUNCH)
    if launch is None:
        return None
    if launch["profile"] is not None:
        selected = launch["profile"] + ".json"
        profile = seen.get(selected)
        if profile is None:
            return None
        if "limit" in profile:
            return [profile["limit"], selected]
    if seen.get(DEFAULT) is not None:
        return [seen[DEFAULT]["limit"], DEFAULT]
    return None


def investigate(policy, read):
    if policy == "defaults_only":
        defaults = read(DEFAULT)
        return [defaults["limit"], DEFAULT] if defaults is not None else None
    seen = {LAUNCH: read(LAUNCH)}
    if policy == "fixed":
        order = [DEFAULT, "blue.json"]
    else:
        launch = seen[LAUNCH]
        if launch is None:
            return None
        profile = launch["profile"]
        order = ([profile + ".json"] if profile is not None else []) + [DEFAULT]
    for path in order:
        result = supported(seen)
        if result is not None:
            return result
        seen[path] = read(path)
    return supported(seen)
