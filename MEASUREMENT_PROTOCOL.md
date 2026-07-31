# Measuring your own silent false-accept rate — the protocol

**A fixed-scope, pre-registered measurement of how often AI-produced changes reach
your mainline wrong while reporting success — run inside your perimeter, against
your own tests, with rules committed before the first data point. Your code never
leaves. At the end you hold a number that is yours, and the method to recompute it
without me.**

This document is the entire method. It is public so that (a) you can judge it
before talking to me, (b) your engineers can challenge it, and (c) after the
engagement you can re-run it yourselves — the deliverable includes everything
needed for that. If you want the measurement run for you: fixed duration
(two weeks), fixed price agreed before day 1, no subscription, no per-seat
anything.

Why you might trust the operator: three published measurements, each with scoring
rules committed **before** the result existed, including one that went against my
own tool and was published anyway — [RESULTS.md](RESULTS.md),
[Study #1](check/study-artifacts/RESULTS.md),
[Study #3](selfreport/RESULTS.md), [PREREGISTRATION.md](PREREGISTRATION.md).
All three are written up as a citable preprint,
[doi.org/10.5281/zenodo.21721312](https://doi.org/10.5281/zenodo.21721312) (CC BY 4.0).
This protocol applies the same discipline to your pipeline.

---

## 1. The question this answers

Benchmarks score agents on how many bugs they fix. The number that decides whether
you can trust an agent inside CI is different: **of the AI-produced changes that
reach your mainline with a green status, how many are wrong?** That is the silent
false-accept rate — *silent* because nothing in a normal pipeline distinguishes
"verified correct" from "the change satisfied checks it was allowed to influence."

On a public benchmark, the measured gap was 17/50 shipped wrong ungated vs 0/50
behind independent verification ([RESULTS.md](RESULTS.md)) — with the cost
published next to it. That is a benchmark number. **This protocol produces the
same class of number for your pipeline, on your changes, against your oracle.**

## 2. Why this needs your perimeter — and why that's a feature

A false-accept rate requires an oracle: something that decides "wrong"
independently of the change being judged. Public benchmarks ship hidden reference
tests; your private code does not — which is why the free public instrument
([`self-check/`](self-check/)) refuses to run on private repos
([WHERE_THIS_STOPS.md](self-check/WHERE_THIS_STOPS.md)).

Your perimeter, however, contains something a benchmark lacks: **your own
pre-existing test suite, CI history, and incident record.** Those are oracles that
already exist, are richer than any synthesized check, and are independent of any
proposing agent — provided the measurement never trusts a test that the change
under judgement itself edited. That fix-blind rule is the core of the method.

Hence the design constraint that shapes everything below: **the measurement comes
to the code; the code never comes to the measurement.** All runs execute on
infrastructure you control. Model-assisted steps, where used, run on endpoints you
approve — including fully local options. Nothing in the method requires your
source, diffs, test names, or ticket text to leave your network.

## 3. Design — two parts, one number each

### Part A — what already shipped (history audit, week 1)

Scope: the last **N merged AI-produced changes** (N fixed in pre-registration;
identified by whatever attribution your org already has — bot accounts, tool
trailers, PR labels, or a team-maintained list).

For each: did your own history later contradict it? Reverts, follow-up fixes
touching the same lines, incident links, hotfixes. Two outputs:

- **Realized wrong-merge count** — changes your own record shows were wrong,
  as a count over N with an exact interval.
- **Detection latency** — for each realized case: time from merge to the moment
  your record shows it was caught, and *what* caught it (a test, a teammate,
  a customer, a later change).

Honest bound, stated in the report: history only shows failures you have already
found. Part A is a **floor**, not the rate. Latent wrong merges are invisible to
it — that is exactly what Part B exists for.

### Part B — what ships during the window (prospective, both weeks)

Every AI-produced change that enters review during the window gets, in parallel
with your normal process, an **independent verification pass** on a clean
checkout inside your perimeter:

1. **Scope conformance** — does the change stay within what its task declared?
2. **Fix-blind test integrity** — the pass never trusts a test the change itself
   added or edited; those are set aside and reported.
3. **Regression run** — your own existing suite, executed in isolation against
   the change, excluding tests from (2).
4. **Acceptance against the stated intent** — checks authored from the
   task/ticket text *before* looking at the change, where the ticket is specific
   enough to allow it; where it isn't, that is recorded as "could not verify",
   never guessed.

Each change lands in one of three states — **verified / needs review / blocked**
— and the disposition is compared with what your normal process actually did.

**The headline of Part B:** of the changes your normal process shipped (or would
have shipped), how many failed independent verification — as a count, with the
full disposition table, and with every blocked-but-actually-fine case listed as
the measurement's own cost. Both error directions are reported; neither is
netted away.

One asymmetry to understand before you buy: a change that *fails* independent
verification is strong evidence something is wrong (a failing test on a clean
checkout is a fact). A change that *passes* is verified only as far as your suite
reaches — coverage limits are inherited, and the report says where.

## 4. What counts — definitions frozen before day 1

Committed to your repo, adapted from the public template
([PREREGISTRATION_TEMPLATE.md](self-check/PREREGISTRATION_TEMPLATE.md)), before
any data is collected:

- what qualifies as an "AI-produced change" in your org, and the attribution rule;
- the window, N for Part A, and the minimum-N honesty rule: if the window yields
  fewer changes than pre-registered, the report says so and publishes counts —
  it does not extrapolate a rate from too little data;
- the oracle inventory: which suites, which CI jobs, which incident sources count;
- the disposition rules above, verbatim;
- exclusions (vendored code, generated files, revert-of-revert chains), each with
  a reason;
- **your team's prediction**, written down first. Not because you must be right —
  because the gap between predicted and measured is half the value.

Pre-registration lives in **your** git history. Your commit timestamps are the
proof that the rules preceded the result — you never have to take my word for it.

## 5. What leaves your perimeter

**By default: nothing.** Source, diffs, test names, ticket text, the report
itself — all stay inside. The report is written on your infrastructure and
reviewed by you. I quote nothing, anywhere, ever, without written approval.

One narrowly-defined option, entirely opt-in: contributing **three anonymized
counts** (changes measured / failed verification / measurement cost) to a
cross-organization base-rate corpus. No company name, no stack details, no dates
finer than a quarter. Why it exists: nobody currently knows the production base
rate of silently-wrong AI changes — every published number, including mine, is a
benchmark proxy. Five to ten perimeters answer a question no benchmark can.
Declining it changes nothing about the engagement.

## 6. Deliverables

1. **Your number** — counts first, exact intervals, never a bare percentage.
2. **Full disposition table** — every measured change, its verdict, and the
   comparison with what your process did.
3. **Every flagged case with a root cause** — including the false-rejects, listed
   against the measurement itself, the same way
   [RESULTS.md §5](RESULTS.md) lists mine.
4. **The re-run kit** — the harness configuration, the frozen definitions, and a
   runbook your team executes quarterly without me. The measurement is only worth
   having if the second one is cheap and yours.
5. **The conversation you actually wanted:** where the failures concentrate
   (task-writing? test coverage? a specific change class?) — the report separates
   what was measured from what I merely think, and labels which is which.

## 7. What this is not

- **Not a certification.** Two weeks, one pipeline, exact intervals — the report
  claims what n supports and no more.
- **Not a capability evaluation.** No solve rates, no model rankings, no
  "your agent got smarter". Wrong axis, on purpose.
- **Not a tool deployment.** The engagement leaves behind a method and a number,
  not a dependency on me or on any product. If, after seeing the number, you want
  a standing verification layer in your pipeline, that is a separate conversation
  — deliberately not bundled, so the measurement stays honest.
- **Not a security audit,** and not a review of human-written code.

## 8. What it costs you internally

- Read access for the harness **on your machines** — nothing outbound;
- an isolated runner able to execute your suite on a clean checkout (a CI slot
  or one container host);
- 2–3 hours of one senior engineer: attribution rules, oracle inventory,
  pre-registration sign-off;
- for Part A: access to merge history and whatever incident links exist.

## 9. Logistics

Two weeks end-to-end. Fixed price, agreed before day 1 — after the
pre-registration scope is set, the price does not move. One engagement at a time.

Contact: [LinkedIn](https://www.linkedin.com/in/dmitriy-kolesnikov-631b67169/) ·
or open an issue in this repository.

---

*Protocol version 1.0 (2026-07-31). Changes to this document are versioned; an
engagement runs on the version committed in its pre-registration. Prose licensed
CC BY-NC 4.0 like the rest of this repository — you may run this protocol on
yourselves freely; that is the point of publishing it.*
