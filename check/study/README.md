# Study #1 — the harness

Runs the study described in [`../PREREGISTRATION_PR_STUDY.md`](../PREREGISTRATION_PR_STUDY.md).
Not shipped on PyPI: this is the research harness, and it lives in the repository
so the study can be reproduced rather than taken on trust.

Pure stdlib. No dependencies, including no `requests`.

## Order of operations — and why they are separate commands

```bash
python -m study auth                 # does the token work? 5 seconds, do it first

python -m study frame                # §3  build + freeze the repository frame
python -m study enumerate            # §3  list every merged PR in the window
python -m study draw                 # §3  seeded stratified draw of 3000
git add study-artifacts/ && git commit -m "study: freeze frame and draw"

python -m study fetch                # §3  download diffs (resumable, hours)
python -m study score                # §2  run the pinned instrument
python -m study report               # §5  RESULTS.md + summary.json
```

## The token

A GitHub token is required — unauthenticated is 60 requests/hour and the study
needs thousands. It is looked for in this order:

1. `$GITHUB_TOKEN` — good for one session;
2. `$GITHUB_TOKEN_FILE` — a path you choose;
3. `~/.patchward-study-token` — the default, one line, nothing else.

The file exists because this study runs over days and a session variable has to
be retyped in every new terminal. Its default location is **outside the
repository** on purpose: a token inside a public working tree is one `git add -f`
away from being published. A leading BOM and trailing newlines are stripped, so
a file written by Notepad works — that failure mode costs an hour to diagnose
because GitHub answers a plain `401`.

`python -m study auth` resolves the token, masks it, confirms GitHub accepts it,
and prints the remaining budget. Run it before anything long.

The stages are separate on purpose. The frame and the draw are committed
**before** any diff is fetched, so the sample provably predates every verdict.
A single `run()` would make it possible — and eventually tempting — to redraw
after glimpsing a number.

`score` refuses to run against a dirty working tree, because contract §2 pins
the instrument to a commit. `--allow-dirty` exists for throwaway runs whose
numbers you then throw away.

## The blind review — the part that matters

```bash
python -m study review               # §4  export 60 flagged + 60 unflagged, shuffled
python -m study serve                # classify them in a local browser UI
git add study-artifacts/review_sample.jsonl && git commit -m "study: blind review"

python -m study tally                # NOW fold against the key
python -m study report               # regenerate with the precision number
```

`serve` opens one case per screen on `127.0.0.1`: the diff, the pull request
description, and five keys. It saves to disk after **every** answer, so it can be
closed and resumed, and it reads nothing but the review sheet — `review_key.json`
is never opened by the server, which is checked by a test rather than asserted in
prose.

Reviewing 120 cases by hand-editing JSON is possible and is how this goes wrong:
attention drifts around item forty, and a careless review produces a precision
number that means nothing while looking exactly like one that does. The UI exists
for that reason alone.

The ordering matters and is the whole protocol: **commit the classifications
before running `tally`.** `tally` is the step that touches the unblinding key. Git
history is what shows the classifications were fixed before anyone knew which
cases the instrument had flagged.

`review` fetches each pull request's description as well as its diff, because
rubric category 2 — *justified expectation change* — turns on whether the PR
**states** an intentional change. Use `--no-bodies` to skip that if you are
offline; the review is weaker without it.

## Checking a published result

```bash
python -m study verify
```

Recomputes every headline figure from `results.jsonl` and exits non-zero on any
drift, including a disposition table that does not sum to the draw. It is meant
to be able to fail — the offline tests include a case where a tampered summary
is caught.

## Tests

```bash
python study/test_stats.py       # intervals, incl. reproducing the published held-out CIs
python study/test_pipeline.py    # draw determinism, disposition, blind-review export
python study/test_matched_analysis.py   # Analysis 2: the strata rule, on data with no effect in it
```

`test_stats.py` reproduces the `17/50 → [21.2%, 48.8%]` and `0/50 → [0.0%, 7.1%]`
figures already published in [RESULTS.md](https://github.com/kolesnikov-arch/patchward/blob/main/RESULTS.md).
If it ever stops doing so, one of the two implementations is wrong and the study
does not run until that is settled.

## A note on the interval code

`study/stats.py` does not reuse `self-check/fa_patchward/stats.py`. That routine
sums `math.comb(n, i) * p**i * (1-p)**(n-i)` directly, which is exact at n = 50
and raises `OverflowError` at n = 3000 — `math.comb(3000, 1500)` is an integer
around 10^902 and `p**i` has long since underflowed to zero. The study computes
the same quantity through the regularized incomplete beta function instead. Both
agree wherever the original still works, which `test_stats.py` checks.

## What is written where

| path | what | committed? |
|---|---|---|
| `study-artifacts/frame.json` | repository frame, inclusions **and** exclusions with reasons | yes |
| `study-artifacts/population.jsonl` | every merged PR in the window | yes |
| `study-artifacts/sample.json` | the drawn 3000, with seed and allocation | yes |
| `study-artifacts/results.jsonl` | one row per drawn PR, always | yes |
| `study-artifacts/review_sample.jsonl` | blind review sheet | yes |
| `study-artifacts/review_key.json` | unblinding key | yes, *after* the review |
| `study-artifacts/RESULTS.md`, `summary.json` | the report | yes |
| `cache/` | raw HTTP responses and diffs | **no** — gigabytes, and rebuildable |
