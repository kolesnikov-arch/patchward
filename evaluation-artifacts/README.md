# Evaluation artifacts — held-out 50 (reproduction kit)

Everything needed to **verify the published number** without access to the private
engine: the exact predictions both arms produced, the raw per-instance evaluation
reports, the paired results table, the task selection, and a script that recomputes
every headline figure from these files.

Two things are reproducible here, by design (see [PREREGISTRATION.md](../PREREGISTRATION.md)):

1. **Verify our number** — re-score the shipped predictions with the public SWE-bench
   harness and recompute the counts, CIs, and the Fisher test.
2. **Reproduce the selection** — re-derive the held-out task set from the frozen,
   seeded selection rules.

What is *not* here is the generation side (the engine that produced the gated arm's
patches and verdicts) — it is private by design; the claims are checkable without it.

## Contents

| Path | What it is |
|---|---|
| `predictions_gated.jsonl` | 50 predictions of the **gated** arm, exactly as evaluated (SWE-bench format) |
| `predictions_ungated.jsonl` | 50 predictions of the **ungated** arm, exactly as evaluated |
| `reports/gated/` · `reports/ungated/` | raw per-instance SWE-bench `report.json` (gold verdict: `resolved`, FAIL_TO_PASS / PASS_TO_PASS detail) |
| `results_paired.csv` · `RESULTS_TABLE.md` | the per-instance paired table: both arms, same task, verdicts + gold outcomes |
| `verify_counts.py` | stdlib-only script: re-derives outcomes from `reports/`, re-tallies the disposition, recomputes 95% Clopper-Pearson CIs + Fisher exact p |
| `selection/` | `held_out_task_ids.txt` (the frozen 50) · `prior_instance_ids.txt` (63 excluded tuning ids) · `select_held_out.py` (seeded selection, reproducible) |
| `test_touching_originals/` | the unmodified originals of the two ungated patches that edited test files (see note below) |

## Re-score it yourself (3 commands)

```bash
pip install swebench
python -m swebench.harness.run_evaluation \
    --dataset_name SWE-bench/SWE-bench_Lite \
    --predictions_path predictions_gated.jsonl \
    --run_id reverify_gated --cache_level env
# then the same with predictions_ungated.jsonl, and:
python verify_counts.py
```

`verify_counts.py` alone recomputes everything from the shipped `reports/`; the
Docker re-evaluation additionally regenerates those reports from scratch (hours,
tens of GB of images).

## Notes for auditors

- **Run labels.** `model_name_or_path` is set to `gated-arm` / `ungated-arm`. This
  label field was renamed from an internal run codename for publication — it is the
  only field touched; every `model_patch` is byte-exact as evaluated. (The label has
  no effect on SWE-bench scoring; it only names the output folder on re-runs.)
- **Both arms, same proposer.** The patch-writing model is identical across arms,
  invoked through the same interface. The arms differ only in process:
  ungated = the model's patch ships as-is; gated = an independent verdict layer
  decides (Verified / Needs review / Blocked).
- **Test-touching predictions (2 cases, pre-registered rule).** SWE-bench convention:
  predictions are source-only — the harness owns the test files. Two ungated patches
  edited tests and collided with the reference test patch; per the rule registered in
  [PREREGISTRATION.md](../PREREGISTRATION.md) before the result, their test hunks were
  stripped and the source fix evaluated on its own. The originals are preserved in
  `test_touching_originals/`, because the two cases differ in kind and both count:
  - `sympy__sympy-16503` — the ungated arm shipped a **wrong** source fix *and
    rewrote the existing test to expect its own wrong output*. Source-only eval:
    not resolved → silent false-accept. The test rewrite itself is a finding.
  - `sympy__sympy-22005` — the ungated arm added **correct** test cases alongside a
    correct source fix. Source-only eval: resolved → shipped correct.
  The rule is symmetric: it neither shields the ungated arm's tampering nor denies
  its legitimate solve.
- **Gated-arm blocked instances still have predictions.** For blocked outcomes the
  gated arm's candidate patch was still captured and evaluated (that is how
  false-rejects are counted against us). "Blocked" means the layer refused to ship
  it, not that no patch existed.
- **Re-runs.** Non-completion flakes (wall-clock timeout with the model still
  iterating, one crashed role call) were re-run once at the frozen timeout, every
  run recorded; a rendered verdict was never re-rolled. Full log in
  [RESULTS.md](../RESULTS.md).

## License

Content and results: CC BY-NC 4.0 (see repository [LICENSE](../LICENSE)).
The predictions include diffs of the respective open-source projects' code, which
remain under those projects' own licenses.
