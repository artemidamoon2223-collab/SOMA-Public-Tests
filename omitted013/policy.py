"""Hand-written investigators. None receives the oracle or fixture mode."""
import ast

KNOWN = ("defaults.json", "profile.json")


def dependencies(source):
    """Parse the fixture grammar: a single left-to-right union of read calls."""
    def walk(node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return walk(node.left) + walk(node.right)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "read" and len(node.args) == 1 and not node.keywords
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            return [node.args[0].value]
        raise ValueError("unsupported loader")
    return walk(ast.parse(source).body[0].value)


def inspect_and_test(known, baseline, inspect, probe):
    paths = dependencies(inspect())
    target = paths[-1]
    outcome = probe(target)
    if outcome == 91:
        return target
    if outcome == "no_key":
        fallback = paths[-2]
        if fallback in known and known[fallback] == baseline:
            return fallback
    return None


def investigate(arm, known, baseline, inspect, probe):
    matches = [path for path in KNOWN if known[path] == baseline]
    if arm == "inspect_first" or (arm == "expand_on_contradiction" and not matches):
        return inspect_and_test(known, baseline, inspect, probe)
    if arm == "verify_known":
        for path in matches:
            if probe(path) == 91:
                return path
        return None
    if len(matches) == 2:
        return matches[0] if probe(matches[0]) == 91 else matches[1]
    return matches[0] if matches else None
