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
patches. The fixes are in
[`../patchward_check/retracted.py`](../patchward_check/retracted.py) and every
one of those false positives is now a regression test in
[`../tests/test_retracted.py`](../tests/test_retracted.py).

After the fixes the rate on those three projects was about 6%, which is where
this note nearly ended. Except that I had picked those three projects myself,
which makes a good result a fact about my taste rather than about the tool.

One more false positive turned up from pointing the tool at its own repository:
editing the **module docstring of a test file** was reported as three retracted
expectations. The fix is that prose at the head of a file is prose. It is
deliberately not "the first lines of a file do not count" — an expected literal
near the top is still an expectation, and a test pinning that down was already
in the suite and failed when the cruder rule went in. The cruder rule was
removed rather than the test.

## How the repositories were chosen

Drawn from [`../study-artifacts/frame.json`](../study-artifacts/frame.json) —
the 150-repository frame built and committed for Study #1 months before this
view existed. That is the whole point of using it: the population could not have
been picked to suit the outcome.

The sample is **grown in waves, never re-drawn**. Wave 1 (four per language
group, seed `20260808`) was scanned and published before wave 2 existed. Wave 2
(eight per group, seed `20260809`) draws only from what wave 1 left. Appending
cannot quietly replace a result that came out inconveniently, and running
`draw.py` shows wave 1 is still the same twelve.

```bash
python check/field-run/draw.py          # wave, group, repository
pip install patchward-check==0.2.3
python check/field-run/scan.py clones > results.json
```

Bare clones, `--depth 250`: this reads each project's **most recent 250
commits**, not its history.

**One commit in sixty is not read.** A diff larger than 1 MB — vendored trees,
lockfiles, checked-in build output — is counted and skipped. The rule is a byte
cap rather than a timeout on purpose: a timeout excludes different work on a
faster machine, and an exclusion rule that depends on the hardware is not a
rule. Adopting it moved wave 1 from 462 retracting commits to 451, and that cost
is why the number is stated rather than the rule quietly applied.

## What came out

| | wave 1 | wave 2 | all |
|---|---|---|---|
| repositories | 12 | 24 | **36** |
| commits read | 2,777 | 5,525 | **8,302** |
| touching a test file | 931 | 2,491 | 3,422 (41%) |
| **retracting something** | **16.2%** | **21.5%** | **19.7%** |
| of those, 3 lines or fewer | 51% | 59% | 57% |
| of those, too large to itemise | 39% | 29% | 32% |
| commits too large to read | 36 | 90 | 126 (1.5%) |

**The estimate rose every time the sample became less mine.** Three projects I
chose: about 6%. Twelve drawn: 16.2%. Twenty-four more, whose numbers I had
never seen until they were computed: 21.5%. Nothing was discarded between those
figures — wave 1 is in this table unchanged, and the 6% is in the git history of
this file.

<details><summary>Per repository</summary>

| repository | wave | commits | touched tests | retracts | rate | median | max |
|---|---|---|---|---|---|---|---|
| `Wei-Shaw/sub2api` | 2 | 147 | 125 | 64 | 43.5% | 3 | 40 |
| `ollama/ollama` | 2 | 250 | 161 | 108 | 43.2% | 3 | 39 |
| `Fission-AI/OpenSpec` | 1 | 250 | 165 | 103 | 41.2% | 4 | 77 |
| `OpenHands/OpenHands` | 2 | 248 | 163 | 97 | 39.1% | 3 | 57 |
| `microsoft/playwright` | 2 | 250 | 158 | 96 | 38.4% | 2 | 175 |
| `milvus-io/milvus` | 1 | 249 | 175 | 89 | 35.7% | 4 | 227 |
| `hashicorp/terraform` | 2 | 236 | 142 | 81 | 34.3% | 3 | 103 |
| `google-gemini/gemini-cli` | 2 | 250 | 158 | 79 | 31.6% | 3 | 53 |
| `BerriAI/litellm` | 2 | 164 | 122 | 51 | 31.1% | 3 | 24 |
| `github/github-mcp-server` | 1 | 250 | 133 | 70 | 28.0% | 2 | 61 |
| `NousResearch/hermes-agent` | 2 | 238 | 180 | 65 | 27.3% | 3 | 9 |
| `etcd-io/etcd` | 2 | 144 | 54 | 37 | 25.7% | 4 | 67 |
| `firecrawl/firecrawl` | 2 | 235 | 125 | 55 | 23.4% | 2 | 38 |
| `gohugoio/hugo` | 2 | 247 | 119 | 56 | 22.7% | 2 | 149 |
| `vercel/next.js` | 2 | 250 | 115 | 52 | 20.8% | 4.5 | 157 |
| `traefik/traefik` | 1 | 193 | 80 | 39 | 20.2% | 2 | 112 |
| `OpenBB-finance/OpenBB` | 2 | 249 | 75 | 44 | 17.7% | 4 | 34 |
| `odysseus-dev/odysseus` | 2 | 231 | 126 | 39 | 16.9% | 2 | 22 |
| `exo-explore/exo` | 1 | 250 | 70 | 41 | 16.4% | 3 | 21 |
| `roboflow/supervision` | 1 | 250 | 124 | 41 | 16.4% | 3 | 30 |
| `mermaid-js/mermaid` | 2 | 164 | 50 | 26 | 15.9% | 2 | 50 |
| `netdata/netdata` | 2 | 250 | 48 | 39 | 15.6% | 10 | 67 |
| `paperless-ngx/paperless-ngx` | 2 | 236 | 94 | 35 | 14.8% | 2 | 20 |
| `fatedier/frp` | 1 | 241 | 66 | 33 | 13.7% | 4 | 114 |
| `axios/axios` | 2 | 248 | 108 | 30 | 12.1% | 2 | 22 |
| `sveltejs/svelte` | 1 | 100 | 53 | 12 | 12.0% | 3 | 10 |
| `vitejs/vite` | 2 | 250 | 87 | 29 | 11.6% | 2 | 29 |
| `github/spec-kit` | 2 | 244 | 160 | 28 | 11.5% | 2.5 | 17 |
| `coder/code-server` | 2 | 250 | 26 | 22 | 8.8% | 3 | 22 |
| `gogs/gogs` | 2 | 249 | 36 | 20 | 8.0% | 1 | 72 |
| `k3s-io/k3s` | 2 | 245 | 37 | 19 | 7.8% | 2 | 9 |
| `shadcn-ui/ui` | 1 | 248 | 37 | 15 | 6.0% | 3 | 34 |
| `ultralytics/ultralytics` | 2 | 250 | 22 | 15 | 6.0% | 2 | 14 |
| `clash-verge-rev/clash-verge-rev` | 1 | 249 | 9 | 4 | 1.6% | 3.5 | 8 |
| `Comfy-Org/ComfyUI` | 1 | 250 | 19 | 4 | 1.6% | 2 | 25 |
| `open-webui/open-webui` | 1 | 247 | 0 | 0 | 0.0% | — | — |

</details>

## Reading it honestly

**Nearly one commit in five says something, and 57% of those are three lines or
fewer.** That is the tool working: a short list a reviewer settles in seconds.

**A third are too large to itemise.** On those the output is a sentence saying
how many lines were replaced. That is honest and it is not useful. A large test
rewrite is a large test rewrite; this view has nothing to add to it.

**The rate runs from 0% to 43.5% across thirty-six projects.** Whatever this
measures, it is at least as much a property of how a project maintains its tests
as of any individual change. Comparing these rates between projects would be a
mistake.

**`open-webui/open-webui` scored zero across 247 commits — because it contains
three test files in total.** This is the result worth sitting with. Where there
is nothing to retract the tool is silent, and silence is indistinguishable from
a clean bill of health. An instrument that cannot tell "nothing was retracted"
from "nothing was ever checked" will mislead exactly the people who most need
telling. That is why `scan --format retracted` prints, under its findings, how
many of the commits it read touched a test file at all.

**And the limits of the run itself:** 250 commits per project is a recent slice,
not history; thirty-six projects out of a frame of 150 still leaves wide
intervals around every rate above; one commit in sixty was too large to read;
and the frame was assembled for a different study with its own inclusion rules,
described in its own contract.
