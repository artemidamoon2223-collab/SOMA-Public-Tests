"""Read-only provenance observation for cooperative, local synthetic Python programs."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch


class Document(str):
    pass


class Value(str):
    pass


class Mapping(dict):
    def __getitem__(self, key):
        result = super().__getitem__(key)
        if key == "value" and type(result) is str:
            result = Value(result)
            result.origin = self.origin
        return result


def observe():
    read = Path.read_text
    loads = json.loads
    dumps = json.dumps
    sinks = []

    def read_tagged(path, *args, **kwargs):
        result = Document(read(path, *args, **kwargs))
        result.origin = str(path)
        return result

    def decode(document, *args, **kwargs):
        parsed = loads(document, *args, **kwargs)
        if type(document) is Document and type(parsed) is dict:
            parsed = Mapping(parsed)
            parsed.origin = document.origin
        return parsed

    def encode(value, *args, **kwargs):
        sinks.append([value.origin if type(value) is Value else None, str(value)])
        return dumps(value, *args, **kwargs)

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout), patch.object(Path, "read_text", read_tagged), \
         patch.object(json, "loads", decode), patch.object(json, "dumps", encode):
        runpy.run_path("app.py", run_name="__main__")
    return {"stdout": stdout.getvalue(), "sinks": sinks}


if __name__ == "__main__":
    print(json.dumps(observe()))
