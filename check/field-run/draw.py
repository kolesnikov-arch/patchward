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

#: Waves, in the order they were drawn. A wave is (seed, repositories per
#: language group) and each one draws only from what earlier waves left.
#:
#: Growing the sample this way rather than re-drawing a bigger one is the whole
#: discipline here: wave 1 was published before wave 2 existed, and appending
#: cannot quietly replace a result that came out inconveniently. Anyone can
#: check that by running this file — wave 1 still prints the same twelve.
WAVES = [
    (20260808, 4),    # published 2026-08-08
    (20260809, 8),    # extension, same day
]
FRAME = pathlib.Path(__file__).resolve().parents[1] / "study-artifacts" / "frame.json"


def draw(waves=None):
    """Yield (wave_number, repository) for every repository in the sample."""
    included = json.loads(FRAME.read_text(encoding="utf-8"))["included"]
    taken = set()
    for n, (seed, per_group) in enumerate(waves or WAVES, start=1):
        rng = random.Random(seed)
        for group in ("python", "js-ts", "go"):
            # Sorted first: `random.sample` over an arbitrarily ordered list
            # would make the draw depend on the frame file's key order rather
            # than on the seed, and the point of the seed is repeatability.
            grp = sorted((r for r in included
                          if r["group"] == group and r["full_name"] not in taken),
                         key=lambda r: r["full_name"])
            for r in rng.sample(grp, min(per_group, len(grp))):
                taken.add(r["full_name"])
                yield n, r


if __name__ == "__main__":
    for wave, r in draw():
        print(f"{wave}  {r['group']:7s} {r['full_name']}")
