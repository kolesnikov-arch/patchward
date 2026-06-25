# patchward

**A verdict layer for AI coding agents — so an agent can't quietly ship a broken fix.**

> 🚧 **Pre-release.** This is the public *proof + concept* home for the Verdict Layer
> approach. The hardened engine is private by design; what's public here is the
> **evidence** and a **live demo**, so you can check the claims yourself.

---

## The number nobody benchmarks

AI coding agents are scored on **resolve rate** — how many bugs they fix. Almost
nobody publishes the number that actually decides whether you can trust an agent in
your CI: the **false-accept rate** — how often an agent *confidently ships* a fix
that looks right and silently isn't.

It gets worse, because agents grade their own homework:

> the agent writes the fix → the agent writes a test for it → the test passes
> (it encodes the agent's *own* misunderstanding) → the agent reports success.

Green checkmark, hidden bug. On a benchmark that looks like a win. In production it's
the regression that fires under load.

## The approach: separate generation from judgement

A probabilistic LLM **proposes**; a deterministic governance layer **decides**.
Independent gates, not the agent itself, render the verdict — and there are three
honest outcomes, not a binary pass/fail:

- 🟢 **Verified** — independently confirmed (e.g. existing tests pass in an isolated
  container; the change is in scope and doesn't regress).
- 🟡 **Unverified** — plausible, but not independently confirmed → flagged for human
  review. The system is honest about what it *couldn't* check, instead of rubber-stamping.
- 🔴 **Blocked** — caught by a gate (edit outside declared scope, failed check, regression).

The point is **accountability**: turn an unaccountable AI patch into one that carries
a verdict and an audit trail — with or without test execution.

## How the verdict is formed

Independent, deterministic checks — for **scope**, **evidence**, and **regression** —
render the verdict, not the agent. Most of them don't require executing code, so they
work offline, air-gapped, in any language; an isolated test run is an additional
confirmation layer when a runtime is available.

The architecture patterns behind this — the governance pipeline and the boundary
between the model's judgement zone and the deterministic enforcement zone — are
documented (abstracted, with implementation and tool names stripped) in the
companion [Verdict Layer Framework](https://github.com/kolesnikov-arch/verdict-layer-framework).
The specific *tuned* engine that implements them stays private.

## What's public — and what isn't

**Public:**
- the concept and the measurement methodology;
- a **reproducible proof-kit** — model predictions + diffs + scoring reports, so you
  can re-run the *scoring* yourself and verify the numbers *(landing as results finalize)*;
- an **interactive sim** of the gates in action *(coming)*.

**Private, by design:** the tuned engine — the gates, the prompts, and the
failure-memory corpus they're tuned against. That tuning, distilled from hundreds of
real runs, *is* the work. We open the **evidence**, not the **engine** — so the claims
are checkable without handing over the moat.

## Status

Pre-release. No headline number is claimed here until it's backed by a published,
reproducible artifact on a held-out set (honesty over hype). The concept and role
ontology live in the companion repo:
[verdict-layer-framework](https://github.com/kolesnikov-arch/verdict-layer-framework).

## License

Concept, documentation, and results: **CC BY-NC 4.0** (matching the
[Verdict Layer Framework](https://github.com/kolesnikov-arch/verdict-layer-framework)).
Demo / sample code (when added): MIT. See [LICENSE](LICENSE).
