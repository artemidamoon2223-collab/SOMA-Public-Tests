"""Continue a trusted public checkpoint using only the inventory and its observed bits."""


def report(files, bits):
    present = sorted(f for f in files if bits.get(f) is True)
    absent = sorted(f for f in files if bits.get(f) is False)
    unknown = sorted(set(files) - bits.keys())
    return {"present": present, "absent": absent, "unknown": unknown,
            "exact": present if not unknown else None}


def prepare(files, prefix):
    if len(set(files)) != len(files):
        raise ValueError("duplicate inventory")
    bits = dict(prefix)
    if (len(bits) != len(prefix) or not set(bits) <= set(files)
            or any(type(value) is not bool for value in bits.values())):
        raise ValueError("invalid observation prefix")
    state = report(files, bits)
    unknown = state["unknown"]
    # All undecided file-membership bits have equal information in these fixtures.
    target = unknown[0] if unknown else None
    return state, target


def finish(files, prefix, target, permitted, probe):
    state, expected = prepare(files, prefix)
    if target != expected:
        raise ValueError("request mismatch")
    if target is None or not permitted:
        return state
    changed = probe(target)
    if type(changed) is not bool:
        raise ValueError("invalid probe")
    return report(files, dict(prefix + [(target, changed)]))
