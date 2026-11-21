"""Challenge a provisional singleton; require coverage before exact attribution."""
from choose import investigate


def decide(catalogue, inventory, allowed, probe):
    observations = {}

    def observe(name):
        changed = probe(name)
        observations[name] = changed
        return changed

    provisional = investigate(catalogue, allowed, observe, adaptive=True)
    challenge = None
    unused = set(allowed) - observations.keys()
    if provisional is not None and unused and len(observations) < 2:
        mentioned = {name for item in catalogue for name in item}
        # Prefer a file omitted by the entire catalogue, then a claimed source.
        target = min(unused, key=lambda n: (n in mentioned, n not in provisional, n))
        result = observe(target)
        challenge = [target, "consistent" if result == (target in provisional) else "refuted"]
    confirmed = sorted(name for name, changed in observations.items() if changed)
    untested = sorted(set(inventory) - observations.keys())
    return dict(provisional=provisional, challenge=challenge, confirmed=confirmed,
                untested=untested, exact=None if untested else confirmed)
