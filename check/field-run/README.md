# Field run — the retracted-expectation view against repositories I did not choose

**What this measures: how loud the view is, and how readable.** It does not
measure whether the view is *right*. Nobody labelled these findings. There is no
ground truth here and no precision figure, and any sentence below that sounds
like one is a sentence to distrust. For what is known about this instrument's
precision — poorly, and why — see
[`../study-artifacts/APPENDIX_precision_by_class.md`](../study-artifacts/APPENDIX_precision_by_class.md).

## Why it exists

`--format retracted` was built and tuned against the held-out evaluation in
[`../../RESULTS.md`](../../RESULTS.md): fifty small, surgical agent patches
produced under laboratory conditions. On those it looked excellent. It had never
read a diff written by a human working on a real project.

The first run against real history was bad. On three well-known projects a
typical flagged commit produced fourteen "retracted expectations", the worst
produced sixty-nine, and the list contained an import statement, a trailing
type-checker comment, a re-wrapped expression and a chunk of a PEM certificate.
None of those is an expectation. All of them fooled rules calibrated on tiny
patches. The fixes that followed are in
[`../patchward_check/retracted.py`](../patchward_check/retracted.py) and every
one of those false positives is now a regression test in
[`../tests/test_retracted.py`](../tests/test_retracted.py).

After the fixes the median on those three projects fell to one to three lines,
which is where this note nearly ended. Except that I had picked those three
projects myself, which makes a good result about my taste rather than about the
tool. So the run was done again, properly.

One more false positive turned up afterwards, and it came from pointing the tool
at its own repository: editing the **module docstring of a test file** was
reported as three retracted expectations. The fix is that prose at the head of a
file is prose. It is deliberately not "the first lines of a file do not count" —
an expected literal sitting near the top is still an expectation, and a test
pinning that down was already in the suite and failed when the cruder rule went
in. The cruder rule was removed rather than the test.

## How the repositories were chosen

Drawn from [`../study-artifacts/frame.json`](../study-artifacts/frame.json) —
the 150-repository frame built and committed for Study #1 months before this
view existed. That is the whole point of using it: the population could not have
been picked to suit the outcome. Four per language group, seed `20260808`
written into `draw.py` rather than passed on the command line.

```bash
python check/field-run/draw.py          # prints the same twelve, always
```

Bare clones, `--depth 250`, so this reads each project's **most recent 250
commits**, not its history.

```bash
pip install patchward-check==0.2.2
python check/field-run/scan.py clones > results.json
```

## What came out

`results.json` holds the numbers below.

| | |
|---|---|
| repositories | 12 |
| commits read | 2,777 |
| commits touching a test file | 951 (34%) |
| commits retracting something | **462 (16.6%)** |
| of those, 3 lines or fewer | **238 (52%)** |
| of those, too large to itemise | **182 (39%)** |

| repository | commits | touched tests | retracts | rate | median | max |
|---|---|---|---|---|---|---|
| `Fission-AI/OpenSpec` | 250 | 167 | 104 | 41.6% | 4.5 | 77 |
| `milvus-io/milvus` | 249 | 179 | 92 | 36.9% | 4 | 281 |
| `github/github-mcp-server` | 250 | 134 | 70 | 28.0% | 2 | 61 |
| `traefik/traefik` | 193 | 82 | 41 | 21.2% | 2 | 112 |
| `exo-explore/exo` | 250 | 72 | 42 | 16.8% | 4 | 21 |
| `roboflow/supervision` | 250 | 125 | 41 | 16.4% | 3 | 30 |
| `fatedier/frp` | 241 | 66 | 33 | 13.7% | 4 | 114 |
| `sveltejs/svelte` | 100 | 54 | 12 | 12.0% | 3 | 10 |
| `shadcn-ui/ui` | 248 | 42 | 19 | 7.7% | 2 | 34 |
| `Comfy-Org/ComfyUI` | 250 | 20 | 4 | 1.6% | 2 | 25 |
| `clash-verge-rev/clash-verge-rev` | 249 | 10 | 4 | 1.6% | 3.5 | 8 |
| `open-webui/open-webui` | 247 | 0 | 0 | 0.0% | — | — |

## Reading it honestly

**16.6%, not the 6% the hand-picked three suggested.** The number I would have
published was wrong by a factor of nearly three, and it was wrong in the
flattering direction, which is the direction to expect when you chose the sample.

**Half the flagged commits are three lines or fewer.** That half is the tool
working: a short list a reviewer settles in seconds.

**Two fifths are too large to itemise.** On those the output is a sentence
saying how many lines were replaced. That is honest and it is not useful. A
large test rewrite is a large test rewrite; this view has nothing to add to it.

**The rate varies from 0% to 41.6% across twelve projects.** Whatever this
measures, it is at least as much a property of how a project maintains its tests
as of any individual change. A cross-project comparison of these rates would be
a mistake.

**`open-webui/open-webui` scored zero across 247 commits — because it contains
three test files in total.** This is the result worth sitting with. Where there
is nothing to retract the tool is silent, and silence is indistinguishable from
a clean bill of health. An instrument that cannot tell "nothing was retracted"
from "nothing was ever checked" will mislead exactly the people who most need
telling.

**And the limits of the run itself:** 250 commits per project is a recent slice,
not history; twelve projects out of a frame of 150 is a small draw with wide
intervals around every rate above; and the frame was assembled for a different
study with its own inclusion rules, which are described in its own contract.
