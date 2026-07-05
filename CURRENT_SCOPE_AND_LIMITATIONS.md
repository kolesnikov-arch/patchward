# Current Scope & Limitations

What this work does **not** yet show — listed first, on purpose. A trust project that hides
its limits has already failed its own thesis.

This is the **measurement-level** scope: the limits of the specific benchmark and runs that
produce the evidence here. For the thesis-level framing, see the companion
[Verdict Layer Framework](https://github.com/kolesnikov-arch/verdict-layer-framework).

## Scope of validation

- **Benchmark only, not production.** The trust measurement runs against a hermetic benchmark
  oracle (a public software-engineering benchmark, SWE-bench Lite, with per-instance
  environments) — **not** a live client CI or a real production merge. Whether a benchmark
  false-accept predicts real engineering risk is the top open question, not a settled fact.
- **One ecosystem so far.** All instances to date are Python repositories. No claim is made
  about other languages or build systems yet.
- **Held-out number: published.** The headline figure now comes from a frozen, seeded,
  never-tuned-on held-out set of 50 instances — see [RESULTS.md](RESULTS.md), reported
  against the [pre-registered contract](PREREGISTRATION.md). Dev-set figures remain
  development feedback, not evidence; only the held-out result is claimed. One held-out
  evaluation exists so far — replication (a second set, other benchmarks) is future work,
  not something this result already proves.

## Measurement caveats

- **Proposer stochasticity is real and only budgeted, not quantified.** The same task can
  yield different outcomes across re-runs (the proposer is noisy). The held-out run used a
  fixed re-run policy set before the run — re-run **non-completions only** (crash/timeout),
  once, at the frozen timeout, every run recorded, verdicts never re-rolled — which bounds
  the flake channel but does not measure run-to-run outcome variance itself.
- **Independent verification reduces coverage in some cases.** To avoid wrongly rejecting a
  correct change, the regression check skips existing tests that the reference solution's own
  test changes touch. Where that removes all regression coverage for an instance, the decision
  leans on the acceptance test alone — a tradeoff still being measured. (Example: an instance
  with no pass-to-pass coverage at all is, by construction, a case where a confident accept
  would rest on the acceptance test alone — exactly the kind of case the held-out set is meant
  to characterize, not to be rule-patched in advance.)
- **Two characterized false-reject classes remain (held-out-confirmed).** The held-out run
  confirmed the calibration on the trust side (no confident vouch of a wrong fix) and
  surfaced five false-rejects in two known classes: the fix-blind acceptance-test author
  can produce environment-incompatible test code, and the regression check is imprecise in
  both directions (it blocked three gold-correct fixes and missed one real test break).
  All five are disclosed with root causes in [RESULTS.md](RESULTS.md) §5; fixing them is
  the next evaluation's delta, measured on a fresh set against the same rules.

## Threats to validity

- **Construct validity:** the benchmark oracle (reference tests) is a *proxy* for "the change
  is correct." A change can satisfy or violate the oracle without that perfectly matching
  real-world correctness or risk.
- **External validity:** results are Python / SWE-bench Lite only. Generalization to other
  languages, repositories, task formats, and live CI is unproven.
- **Oracle assumptions:** independent verification assumes the requirement text plus the base
  repository are enough to author a fix-blind acceptance test, and that the existing pass-set
  minus the reference-touched tests is a sound regression set. Both are reasonable, not proven.

## Current evidence base

- **The private failure corpus is self-dogfood.** It was accumulated by the system repairing
  itself — disciplined and classified, but **not** an externally diverse corpus. External
  diversity comes from the benchmark work, which is in progress.
- **Independent verification is benchmark-wired, not client-wired.** It has been demonstrated
  against a benchmark oracle; wiring it to a real client's CI/runtime is not started. Do not
  read "blocks bad changes in the benchmark" as "blocks bad changes in production."

## Negative results are retained

Hypotheses that fail validation are **kept** as part of the project history, not deleted. The
measurement evolves through rejected assumptions as much as confirmed ones. (Example: a
regression failure on one instance was hypothesized to be an instrument artifact; the
independent oracle rejected that hypothesis — it was a genuine bad change — and the instrument
was left unchanged. Losing a hypothesis to the arbiter is a result, not a failure.)

## What we explicitly do NOT claim

- We do **not** make the model smarter or raise solve rate. By design — the value is on the
  trust axis, not capability.
- We do **not** claim to define an industry standard. We publish reproducible measurements;
  adoption, if any, is earned later.
- We do **not** claim novelty of the *concept* of admission control / gating. The claim is a
  calibrated, leak-safe, independently verifiable **measurement** of trust, with the evidence
  to back it.
