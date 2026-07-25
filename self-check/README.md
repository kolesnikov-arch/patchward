# fa-patchward

**Point it at your coding agent. Get your own number: how many wrong fixes it
ships silently.**

> **Looking for something you can run in a second?** This isn't it — this is the
> research instrument, and it costs a day and a Docker install. For the everyday
> tool, see **[`../check/`](../check/)**: `pip install patchward-check` flags changes
> that rewrite the tests judging them, instantly, on any repository, offline.
>
> *Naming note: on PyPI this instrument is `fa-patchward` — `fa-` is the false-accept
> rate it measures — and the everyday tool is `patchward-check`. The bare `patchward`
> name there belongs to an unrelated project.*

Benchmarks score agents on *capability* — how many bugs they fix. The number that
decides whether you can let an agent into your CI is a different one: the
**silent false-accept rate** — how often it confidently ships a fix that looks
right and isn't. This tool measures *that*, on *your* agent, against a frozen
public benchmark, using the benchmark's own hidden reference tests as ground
truth.

It is a **ruler, not a gate.** It shows you how much leaks; it does not stop the
leak. Read [WHERE_THIS_STOPS.md](WHERE_THIS_STOPS.md) — the boundary is the point.

> This is the **self-check tool that ships with patchward**. The reference result
> in [`../RESULTS.md`](../RESULTS.md) replays one fixed run (the same model
> silently shipped 17/50 wrong fixes ungated vs 0/50 gated). fa-patchward makes the
> same measurement **aimable at your own agent**, with the same honesty
> scaffolding: frozen seeded selection, exact Clopper-Pearson CIs, and a
> recompute-from-evidence verifier. Our number is in `../RESULTS.md`; this gets
> you yours.

## Install

```bash
pip install fa-patchward           # core is pure stdlib
pip install 'fa-patchward[select]' # + `datasets`, to sample tasks
pip install swebench               # the public evaluator (step 3)
```

From source instead (this repo):

```bash
git clone https://github.com/kolesnikov-arch/patchward
pip install -e patchward/self-check
```

Then `fa-patchward init` drops an adapter stub + a pre-registration file into your
working directory so you can start without cloning anything else.

## What you get

```
your-agent: shipped 41 fixes reported as done; 12 were wrong
            -> 12/41 = 29.3% silent false-accept
            95% CI [16.6%, 44.7%]  |  ground truth = benchmark reference tests
```

Plus `report/RESULTS.md` (human-readable), `report/results.csv` (per-instance),
and `report/summary.json`. Abstains (the agent produced nothing) and
apply-failures are shown separately and **never** inflate the number.

## Use it — four steps

**1. Freeze the task set _before_ you look at any number.**

```bash
fa-patchward select --dataset SWE-bench/SWE-bench_Lite --n 50 --seed 50 --out frozen
```

Writes `frozen/tasks.txt` and `frozen/selection.json` (dataset, seed, exclusions,
timestamp). Commit both now — that is what makes the number honest, not vanity.
Have your own held-out list already? `fa-patchward select --from-ids my_tasks.txt`.

**2. Run your agent, ungated, over the set.**

```bash
fa-patchward run --tasks frozen/tasks.txt --agent "python my_agent.py" \
             --label your-agent --out predictions.jsonl
```

Your agent plugs in through one tiny adapter (stdin task JSON → stdout patch
JSON). See [adapters/README.md](adapters/README.md); `adapters/noop_agent.py` is a
complete working example. **Already have `predictions.jsonl`** from aider /
SWE-agent / your own harness? Skip this step entirely.

**3. Evaluate the predictions with the public SWE-bench harness.**

fa-patchward does not re-implement SWE-bench — it reads its output.

```bash
python -m swebench.harness.run_evaluation \
    --dataset_name SWE-bench/SWE-bench_Lite \
    --predictions_path predictions.jsonl \
    --run_id my_run --cache_level env
```

(This is the part that needs Docker and time; it's the same command the reference
kit documents.)

**4. Get your number.**

```bash
fa-patchward report --predictions predictions.jsonl \
             --reports logs/run_evaluation/my_run \
             --tasks frozen/tasks.txt --label your-agent --out report
```

Then, any time, prove the number wasn't massaged:

```bash
fa-patchward verify --report-dir report --reports logs/run_evaluation/my_run \
             --predictions predictions.jsonl --tasks frozen/tasks.txt
```

`verify` recomputes every outcome from the raw reports and fails loudly if
`results.csv` disagrees.

## What "silent false-accept" means here

For each task: your agent produced a patch **and reported it done** (ungated —
whatever it returns is "shipped"), but the benchmark's hidden reference tests
**fail**. That's a silent wrong ship. Producing no patch is an *abstain* — honest,
not counted. A patch that won't apply is an *apply-failure* — infra, not counted.
The headline is `silent_false_accept / (shipped_correct + silent_false_accept)`.

## Verification status (v0.1 — read this before you trust the output)

A trust tool that hides what it hasn't verified has already failed its own thesis.
So, precisely what is and isn't checked:

- ✅ **The scoring is validated on real harness output.** Run against patchward's
  own reference reports, fa-patchward reproduces the published **17/50 (34.0%, CI
  [21.2%, 48.8%])** exactly — bit-identical to `../evaluation-artifacts/verify_counts.py`.
  The reports → your-number path is real, not just synthetic tests. Reproduce it:
  `python tests/test_gauge.py`.
- ✅ **Install + CLI are verified.** `pip install` into a clean environment,
  `fa-patchward init` in an empty directory, and `fa-patchward run` driving an
  adapter end-to-end all work.
- ⚠️ **The live-agent chain is not yet exercised end-to-end by the author.** Wiring
  *your* agent adapter and running the Docker SWE-bench evaluation on fresh
  predictions happens in your environment. If something breaks there, that is a
  bug worth an issue (or a PR) — this is an instrument, not a finished product, and
  it is meant to be corrected in the open. It reports *your* number; it makes no
  claim of its own.

## Honesty scaffolding

Read [PREREGISTRATION_TEMPLATE.md](PREREGISTRATION_TEMPLATE.md) before your first
run and fill it in. A self-check that lets you reshuffle the task set or reroll a
bad outcome is measuring nothing. The whole value is a number you didn't get to
tune.

## Test it without Docker or a real agent

```bash
python tests/test_gauge.py   # stdlib only; incl. the real-data reconciliation above
```

## License

Source code: MIT. Documentation and prose: CC BY-NC 4.0. See [LICENSE](LICENSE).
This tool measures the problem; the engine that fixes it is private by design.
