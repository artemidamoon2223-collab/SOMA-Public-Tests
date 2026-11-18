"""Toy application. Its only stdout is the effective integer setting."""
import json
from pathlib import Path


def config(name):
    return json.loads(Path(name).read_text())


def main():
    limit = config("defaults.json")["limit"]
    profile = config("launch.json")["profile"]
    if profile is not None:
        limit = config(profile + ".json").get("limit", limit)
    print(limit)


if __name__ == "__main__":
    main()
