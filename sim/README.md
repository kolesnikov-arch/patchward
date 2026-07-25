# Verdict Layer — Trust Decision Walkthrough

A small, static visualization of the idea at the center of this framework: **an admission
decision should be formed from independent evidence, not from the agent's self-report.** It
is a conceptual walkthrough, not a deployable product.

## Open

**Live: https://kolesnikov-arch.github.io/patchward/sim/**

Or open `index.html` in any browser. No server, no build, no dependencies. Fully static.

## What it shows

Three scenarios, each walking the same path — *requirement → fix-blind acceptance test →
agent change → independent verification → verdict → decision* — and ending in the
**tri-state** verdict:

- **Verified → Accept.** A correct change. The independent, fix-blind acceptance test and a
  regression check both pass, so the accept is *earned* by evidence the agent did not author.
- **Underspecified → Review.** The requirement states the behavior but not every detail
  (e.g. it says "raise an error" but not which type). The layer verifies the specified part
  and **escalates the rest** instead of guessing — the honest third state.
- **Confidently wrong → Reject.** The agent's *own* test passes (green), so a self-graded
  pipeline would ship it — but the fix-blind acceptance test fails. Independent verification
  catches the confident-but-wrong change.

In every scenario the **agent's own test is shown as passing**. That is deliberate: a test an
agent writes for its own change is self-referential and passes for a right fix and a wrong
one alike, so it is treated as informational, never as the deciding signal.

## Grounded in measured results

The walkthrough artifacts are illustrative, but each scenario now cites its **real measured
counterpart** from the published held-out evaluation (50 pre-registered tasks; ungated
17/50 silent wrong ships vs gated 0/50):

- *Review* ↔ `django__django-13321` — the same near-identical incomplete fix shipped
  silently ungated, and arrived flagged for review gated.
- *Reject* ↔ `sympy__sympy-22840` (a 36-test regression caught and blocked) and
  `sympy__sympy-16503` (the ungated agent rewrote a test to hide its wrong fix).
- *Accept* ↔ honestly: zero confident accepts in that configuration — the disclosed
  thin-oracle conservatism.

Numbers, artifacts, and per-instance table:
[patchward — held-out results](https://github.com/kolesnikov-arch/patchward/blob/main/RESULTS.md).

## What it does NOT include

- Any internal engine, scoring, calibration, or orchestration logic
- Real model output, prompts, or routing
- A real pipeline — the artifacts are illustrative and authored for the walkthrough

## Use

Suitable for explaining the trust thesis in a talk or a README: why capability is not enough,
what independent verification means, and why the decision has three states rather than two.
