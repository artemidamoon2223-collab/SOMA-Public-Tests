"""Limit provenance propagation to whitespace stripping with no arguments."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "repair016"))
import observer


class TracedValue(observer.Value):
    def strip(self, *args, **kwargs):
        result = str.strip(self, *args, **kwargs)
        if args or kwargs:
            return result
        tagged = TracedValue(result)
        tagged.origin = self.origin
        return tagged


if __name__ == "__main__":
    with patch.object(observer, "Value", TracedValue):
        receipt = observer.observe()
    print(json.dumps(receipt))
