# Pre-registered Scoring Contract

**Date-stamped: 2026-07-03 (see this file's git history).**
**Status: the evaluation is IN PROGRESS on a frozen instrument. This document deliberately
contains NO results — that is the point.** The scoring rules, the reporting commitments, and
the answers to the hard objections are fixed *before* the outcome exists, so they cannot be
fitted around it. When the results publish, hold this document against them.

---

## 1. What is being measured

Two arms run on the same task set, with the same underlying model, scored against the
benchmark's **hidden reference tests** — which neither arm can see or touch:

| | Ungated arm | Gated arm (verdict layer) |
|---|---|---|
| What it does | model writes a patch → it ships | model proposes → an independent verdict layer decides |
| Possible outcomes | patch / no patch | 🟢 **Verified** · 🟡 **Needs review** · 🔴 **Blocked** |
| What ships silently | **every patch produced** | only **Verified** |
| Flag channel | none | **Needs review** = patch delivered *plus* an explicit "could not verify — a human decides" |

The verdict comes from independent, deterministic checks (scope, evidence, regression, and —
where a runtime is available — an isolated run of an acceptance test authored **blind to the
fix**, from the requirement alone). The proposing agent never controls its own verdict.

## 2. Scoring rules (the contract)

- **Ungated false-accept** — a shipped patch that fails the hidden reference tests.
  (Producing no patch is a miss, *not* a false-accept.)
- **Gated confident false-accept** — a **Verified** verdict on a patch that fails the hidden
  reference tests. **This is the headline cell.**
- A **Needs-review** patch that turns out wrong is *not* a confident false-accept by contract —
  the flag is an escalation, not a merge — but it is **always reported**, never hidden
  (see the sensitivity row, §3).
- A **Blocked** verdict on a patch that would have passed is a **false-reject** (recall cost).
  Reported with root causes, off-headline.
- **Headline = confident false-accepts (gated) vs. false-accepts (ungated), at comparable
  delivered yield of correct fixes, with the full disposition table published alongside.**
  Never a pass-rate or capability claim.

## 3. Reporting commitments (what the results artifact must contain)

1. **Absolute counts first**, percentages second — never a "−N%" without the counts beside it.
2. **Exact (Clopper–Pearson) binomial confidence intervals** on both arms' false-accept rates.
3. The **full disposition table** for the gated arm (verified / needs-review correct & wrong /
   blocked correct & wrong) and for the ungated arm (shipped correct / shipped wrong / empty).
4. A **sensitivity row**: the pessimistic contract, in which every wrong Needs-review patch is
   counted against the gated arm as if it had been merged — so a reader who distrusts the flag
   channel can score that scenario directly.
5. The **per-instance paired table** (both arms, same task, both outcomes) in a reproduction
   kit, so anyone can recompute every number.
6. The **false-reject list with root causes**, and the **log of any infrastructure-only fixes**
   made during the run (see §5).
7. The **confident-vouch rate** — reported for context, explicitly off-headline (§6).

## 4. Anticipated objections — answered before the result

**"A gate that never vouches trivially has zero false-accepts."**
The headline is false-accept ↓ *at comparable delivered yield*, not false-accept ↓ alone. A
Needs-review outcome still **delivers the patch** — with an honest flag instead of a rubber
stamp. The yield table publishes next to the headline; if the gated arm delivered materially
fewer correct fixes, the number would be an artifact, and the report will say so itself.

**"You count the gated arm's *confident* misses but the ungated arm's *all* misses — asymmetric."**
The comparison models the deployment contract, not label symmetry: an ungated pipeline has no
flag channel — everything it ships is silent by construction. Readers who reject that premise
get the pessimistic sensitivity row (§3.4) and can re-score.

**"The sample is small."**
Yes — hence counts-first reporting and exact binomial CIs (§3.1–2), and the paired per-instance
table so the uncertainty is inspectable rather than narrated.

**"The acceptance test synthesized from the issue text is a weak oracle."**
True, and disclosed. It is *independent* (authored blind to the fix, never touches the hidden
reference), which is what the trust claim needs; it is also *thin*, which mostly costs the
gated arm confident vouches (underspecified issues land in Needs review — conservatism, not
inflation). In real deployments the layer runs the client's own pre-existing test suite — a
richer oracle that is still independent. That upgrade path is roadmap, not part of this result.

**"One run per instance proves nothing — agents are noisy."**
Agreed; run-to-run drift is real and was observed during development. Mitigation, fixed before
the held-out: a re-run budget per instance for **infrastructure non-completions only** (crash,
timeout, empty-by-plumbing), with **every run recorded**. A rendered verdict is never re-rolled
in search of a better class.

**"You tuned the instrument on your own benchmark."**
On the development set — yes, by design and disclosed; that is what a development set is for.
The held-out set is different in kind: selected by a frozen, seeded script from the benchmark's
task pool; **zero instance overlap** with anything ever used for tuning; instrument **frozen at
a pinned commit before the first run** (hash published with the results); and a standing rule
for the whole run: **no change that could alter any verdict on any instance.** Pure
infrastructure failures (a crash that prevents a model call from happening at all) may be
fixed; each such fix is committed separately and logged in the results artifact.

**"The model has seen these repositories in training."**
Plausible — and arm-symmetric: both arms use the same model on the same tasks, so contamination
shifts absolute solve rates, not the gated-vs-ungated comparison. No absolute-capability claim
is made anywhere.

**"This is just CI / a linter / policy-as-code."**
CI runs tests a human already wrote. The question here is what admits an *AI-authored* change
when no human has written its test yet — and whether the admitting checks are independent of
the agent that produced the change. The measured claim is not "we run checks"; it is "the layer
cuts silently shipped wrong fixes on an independent held-out set, at comparable delivered yield."

## 5. Freeze discipline

- Task selection: frozen, seeded script over the public benchmark's task pool; selection code
  and the task list publish with the reproduction kit.
- The held-out set is disjoint from every task ever used to develop or tune the instrument.
- Instrument pinned at a commit before the first held-out run; the pin does not move mid-run.
- Mid-run changes: only infrastructure-only fixes that decide whether a run *happens at all* —
  never how it is judged. Each is committed separately and logged (§3.6).
- Anomalies are **diagnosed before they are scored** — an empty or crashed run is investigated,
  not silently counted.

## 6. What is NOT claimed

- No pass-rate / leaderboard / "beats model X" claim. The layer does not raise solve rate,
  by design.
- No "zero false-accepts": issues whose text underdetermines the hidden tests impose an
  irreducible floor; where it shows up, it will be shown.
- The confident-vouch rate is expected to be conservative in this benchmark configuration —
  it is reported for context and is **not** the pitch.
- No production-CI claim: this validates the method on a public software-engineering
  benchmark; production deployment is a separate, later step.
- No industry-standard claim. These are reproducible measurements on an independent set;
  whatever authority they earn, they earn by being checked.

---

*If the result contradicts the thesis, it publishes anyway, against these same rules.
A negative result with a pre-registered method is still a result; a positive one without
it is just marketing.*
