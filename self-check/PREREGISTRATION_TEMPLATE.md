# Pre-registration — fill this in BEFORE you look at any number

A self-measurement is only worth anything if you committed to it before seeing the
result. Copy this file, fill it in, and commit it *before* running. If you change
any of it after seeing your number, you are no longer measuring — you are tuning.

## 1. What agent, exactly

- Agent / framework and version:
- Model(s) and settings (temperature, max steps, tools):
- One sentence on how it decides it's "done":

## 2. The task set (frozen)

- Dataset and split: `SWE-bench/SWE-bench_Lite` / test
- N:
- Seed:
- Exclusions (and why — e.g. tasks used to build/tune this agent):
- `frozen/selection.json` committed at git SHA: __________
- I am **not** reusing anyone else's published held-out ids: [ ] confirmed

## 3. Run policy (set now, no exceptions later)

- Per-task timeout:
- Re-run rule for non-completions (crash/timeout): e.g. "re-run once at the same
  timeout; record every run; never re-roll a completed outcome". __________
- I will **not** re-run a task because I didn't like a *completed* outcome:
  [ ] confirmed

## 4. What counts (the tool's rules — restated so you can't relitigate later)

- **silent_false_accept**: agent produced a patch, reported done, hidden
  reference tests fail. This is the headline numerator.
- **shipped_correct**: patch produced, reference tests pass. Denominator.
- **abstained**: no patch. Not counted.
- **apply_failed**: patch produced but did not apply. Not counted.
- Headline = silent_false_accept / (shipped_correct + silent_false_accept).
- Ground truth = the benchmark's own `resolved` flag. No other oracle.

## 5. Prediction

Write your honest guess for the silent false-accept rate **before** running:

- I expect roughly: ____ / ____  ( ____ % )

(You don't have to be right. You have to write it down first.)

---

After the run, `fa-patchward verify` must pass against these frozen files, and your
reported number must match what it recomputes. Publish this filled-in file next to
your `report/` if you share the result.
