import ast

DEFAULT = "defaults.json"
PROFILE = "green.json"
EMPTY = [None, None]


def precedence(source):
    if source is None:
        return None
    tree = ast.parse(source)
    for pair in (("defaults", "profile"), ("profile", "defaults")):
        expected = ast.parse("def merge(defaults, profile):\n    return " + " | ".join(pair))
        if ast.dump(tree) == ast.dump(expected):
            return pair[-1]
    raise ValueError("outside the two specified loader grammars")


def investigate(read, eager):
    order = precedence(read("loader.py")) if eager else None
    if order == "defaults":
        defaults = read(DEFAULT)
        if "limit" in defaults:
            return [defaults["limit"], DEFAULT]
    else:
        defaults = None
    if not read("launch.json")["enabled"]:
        if defaults is None:
            defaults = read(DEFAULT)
        return [defaults["limit"], DEFAULT] if "limit" in defaults else EMPTY
    profile = read(PROFILE)
    if order == "profile" and "limit" in profile:
        return [profile["limit"], PROFILE]
    if defaults is None:
        defaults = read(DEFAULT)
    if "limit" not in profile:
        return [defaults["limit"], DEFAULT] if "limit" in defaults else EMPTY
    if "limit" not in defaults:
        return [profile["limit"], PROFILE]
    if not eager:
        order = precedence(read("loader.py"))
    if order is None:
        return None
    return [profile["limit"], PROFILE] if order == "profile" else [defaults["limit"], DEFAULT]
