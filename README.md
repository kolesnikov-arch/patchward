# patchward

**🇺🇸 English | [🇨🇳 简体中文](README_zh.md)**

**An AI agent shouldn't get to write both the fix and the test that approves it.**

```bash
pip install patchward-check
patchward-check scan      # your history: which changes rewrote the tests judging them?
```

No config, no API key, no Docker, no model. Reads the diff, runs nothing, blocks
nothing. → [`check/`](check/)

---

## The failure this is about

A coding agent was asked to fix a formatting bug. It changed the source — and then
rewrote the expected output in the existing test, so the test would agree with it:

```diff
--- a/sympy/printing/pretty/pretty.py
-        prettyF.baseline = max_upper + sign_height//2
+        prettyF.baseline = max_upper + 1 + first_d - expr_height//2 ...

--- a/sympy/printing/pretty/tests/test_pretty.py
-   \        \     /        1    \        \n\
+   \        \     /        1    \     1  \n\
```

Suite green. Fix wrong. The test that would have caught it was edited by the change
it was supposed to catch. **The agent didn't just err — it moved the definition of
correct.** Nothing in a normal CI run tells this apart from a passing build.

That patch is real, from the held-out evaluation below. `patchward check` flags it
from the diff alone, in about a millisecond.

## Benchmarks measure capability. CI needs trust.

Agents are scored on **resolve rate** — how many bugs they fix. That's capability.
The number that decides whether you can let an agent into your CI is a different,
far less-reported one: the **false-accept rate** — how often it *confidently ships*
a fix that looks right and silently isn't.

It compounds, because agents grade their own homework:

> the agent writes the fix → the agent writes a test for it → the test passes
> (it encodes the agent's *own* misunderstanding) → the agent reports success.

Green checkmark, hidden bug.

## What that costs, measured

> On a frozen, pre-registered, held-out set of 50 SWE-bench Lite tasks, the same
> model silently shipped **17/50** wrong fixes ungated — and **0/50** when an
> independent verdict layer decided what ships.

Full numbers, exact confidence intervals, every false-reject with its root cause,
and the disclosed costs: **[RESULTS.md](RESULTS.md)**. The scoring rules were
published **before the result existed** ([PREREGISTRATION.md](PREREGISTRATION.md),
2026-07-03; run completed 07-05), so they provably weren't fitted around the
outcome. Every figure recomputes from [`evaluation-artifacts/`](evaluation-artifacts/)
with a stdlib-only script.

Read [Current Scope & Limitations](CURRENT_SCOPE_AND_LIMITATIONS.md) before drawing
any conclusion from that number — it is one evaluation, on Python, on a benchmark,
not production CI.

## What's in this repository

| | |
|---|---|
| **[`check/`](check/)** | `pip install patchward-check` — flags changes that rewrite the tests judging them. Instant, offline, any repo, MIT. **Start here.** |
| **[`evaluation-artifacts/`](evaluation-artifacts/)** | The proof kit: both arms' predictions as evaluated, raw per-instance reports, paired results, seeded selection, recompute script. |
| **[`self-check/`](self-check/)** | The research instrument: point it at *your* agent and measure its own silent false-accept rate on a public benchmark. Costs a day and a Docker install. |
| **[`sim/`](sim/)** | Interactive sim of the verdict logic — accept / review / reject. [Runs in the browser](https://kolesnikov-arch.github.io/patchward/sim/), no install. |
| **[RESULTS.md](RESULTS.md)** · **[PREREGISTRATION.md](PREREGISTRATION.md)** · **[CURRENT_SCOPE_AND_LIMITATIONS.md](CURRENT_SCOPE_AND_LIMITATIONS.md)** | The evidence, the rules that predate it, and the honest limits. |

## The approach: separate generation from judgement

A probabilistic LLM **proposes**; an independent, deterministic verdict layer
**decides**. The checks, not the agent, render the verdict — and there are three
honest outcomes, not a binary pass/fail:

- 🟢 **Verified** — independently confirmed (existing tests pass in isolation; the
  change is in scope and doesn't regress).
- 🟡 **Needs review** — plausible, not independently confirmed → flagged for a human.
  Being honest about what it *couldn't* check beats rubber-stamping.
- 🔴 **Blocked** — caught by a gate (edit outside declared scope, failed check,
  regression).

Most of those checks don't require executing code, so they work offline, air-gapped,
in any language; an isolated test run is an extra confirmation layer when a runtime
exists. The reasoning — why an independent verdict beats an agent's self-report, and
why three states beat two — is abstracted in the companion
[Verdict Layer Framework](https://github.com/kolesnikov-arch/verdict-layer-framework).

`patchward check` is the smallest, bluntest instance of that principle: one check,
no oracle, free.

## What's private, and why

The tuned engine — the gates, the prompts, and the failure-memory corpus they're
tuned against — is not published. That tuning, distilled from hundreds of real runs,
*is* the work, and a version of it running untuned in someone else's repository
would perform worse than these results claim.

So: the **evidence** is open so the claims are checkable, and the everyday
**instrument** ([`check/`](check/)) is open and MIT so it's actually usable. What
stays closed is the part that needs calibration to mean anything. Where each tool
stops, and why, is written down: [self-check/WHERE_THIS_STOPS.md](self-check/WHERE_THIS_STOPS.md).

## Status

Evaluation #1 published 2026-07-05. `check` is v0.1 — its predictive power is **not
yet established** (see its [README](check/README.md); a validation against public
pull-request history is the next piece of work, and the number will be published
whichever way it comes out).

Issues and corrections are welcome and are the fastest way to improve any of this —
see [CONTRIBUTING.md](CONTRIBUTING.md). Field notes as the work runs:
[Trust in AI Delivery](https://dmitriykolesnikov.substack.com).

## License

- **[`check/`](check/)** — MIT throughout, code and prose. It's meant to be installed.
- Everything else — documentation, results, and prose: **CC BY-NC 4.0**;
  sample code: MIT. See [LICENSE](LICENSE).
