"""Draw the repositories this view was validated against.

The frame is not new. It is `../study-artifacts/frame.json`, built and committed
for Study #1 months before this view existed, which is the only reason a draw
from it means anything: the population could not have been chosen to suit the
result. The seed is written here rather than passed in, so the draw is a fact
about this file and not about how it was invoked.

    python check/field-run/draw.py
"""
import json
import pathlib
import random

SEED = 20260808
PER_GROUP = 4
FRAME = pathlib.Path(__file__).resolve().parents[1] / "study-artifacts" / "frame.json"


def draw():
    included = json.loads(FRAME.read_text(encoding="utf-8"))["included"]
    rng = random.Random(SEED)
    out = []
    for group in ("python", "js-ts", "go"):
        # Sorted first: `random.sample` over an arbitrarily ordered list would
        # make the draw depend on the frame file's key order rather than on the
        # seed, and the point of the seed is that anyone can repeat it.
        grp = sorted((r for r in included if r["group"] == group),
                     key=lambda r: r["full_name"])
        out += rng.sample(grp, PER_GROUP)
    return out


if __name__ == "__main__":
    for r in draw():
        print(f"{r['group']:7s} {r['full_name']}")
