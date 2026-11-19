"""The decision code is given observations only."""
import json


def original_access(rule, primary, initial_value, output, inspect, probe):
    names = inspect()
    target = names[-1] if names else primary
    return target if probe(target) == "changed" else None


def witnessed(output, observation):
    if observation is None or observation["stdout"] != json.dumps(output) + "\n":
        return None
    sinks = observation["sinks"]
    if len(sinks) != 1:
        return None
    source, value = sinks[0]
    if not isinstance(source, str) or not source or value != output:
        return None
    return source
