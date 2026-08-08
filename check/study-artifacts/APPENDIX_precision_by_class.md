# Appendix — what precision by finding class does and does not show

> **Post-hoc. Not pre-registered.** The contract (§5.5, §5.4) required the base rate
> broken out by finding class and one aggregate blind-review precision. Both are in
> [RESULTS.md](RESULTS.md). It did not ask for precision *per class*, and this
> appendix is an analysis run afterwards, on the same published artifacts. Read it as
> an analysis of the study, not as one of its results.

## Why this exists

[RESULTS.md](RESULTS.md) §7 already states the limit: *"with only four confirmed true
positives in the blind review, precision per class cannot be estimated at all."* This
appendix does not overturn that. It puts the arithmetic on the page so the statement can
be checked rather than taken on trust, because a shipped tool now leans on it.

The GitHub Action in this repository defaults to not commenting on pull requests and
gives the aggregate precision as its reason. A reader is entitled to the obvious
follow-up: the aggregate lumps a weak signal in with a severe one, so does the severe
signal do better on its own? If it did, a narrower check might be worth commenting on.

The honest answer is not "no". It is **"this sample cannot tell you, and here is what
that looks like"** — which is the answer that decides the design either way, because a
default that accuses people needs evidence *for* itself, not merely the absence of
evidence against.

## Method

For each of the 120 review cards, the finding classes the instrument recorded come from
`review_key.json`; the blind labels come from `review_sample.jsonl` (pass 1) and
`review_pass2.jsonl` (pass 2). Precision uses the study's own denominator rule from
`study/report.py`: `judged = true positives + false positives`, where class 1 is a true
positive and classes 2–4 are false positives; classes 5 (undecidable) and 6 (flagged but
no test change) are excluded from the denominator and surfaced separately, exactly as in
the headline figure. Recompute with `python -m study verify` and the artifacts here.

## Result

Pass 1; pass 2 differs by at most 0.4 points on every row.

| finding class | confirmed / judged | precision | 95% CI (Clopper–Pearson) |
|---|---|---|---|
| `REWRITTEN_EXPECTATION` | 4 / 54 | 7.4% | [2.1%, 17.9%] |
| `DELETED_TEST` | 1 / 22 | 4.5% | [0.1%, 22.8%] |
| `SUPPRESSED` | 0 / 3 | — | [0%, 70.8%] |
| `NO_NEW_EVIDENCE` | 0 / 1 | — | [0%, 97.5%] |
| `SELF_GRADED` | 4 / 58 | 6.9% | [1.9%, 16.7%] |

**Every interval contains the aggregate, and every interval is enormous.** Four true
positives spread across overlapping classes cannot separate them. `REWRITTEN_EXPECTATION`
— the signal this instrument was built around — lands within half a point of the headline
figure, but a range of 2% to 18% is not a measurement of anything; it is the width of the
ignorance. The correct reading is that **this sample provides no evidence that any class
does better, and equally none that they are the same.**

That asymmetry is the whole point for the tool. A check that stays quiet needs no
evidence. A check that names an author on a pull request needs evidence *for* itself, and
there is none here to have.

**The bottom two rows say nothing at all.** Three cards and one card carry no
information; the intervals are printed to make that visible rather than to be read. They
are here because omitting the classes that happened to score zero would be selection by
outcome.

**`SELF_GRADED` is the aggregate, not a fifth measurement.** It fires on every flagged
pull request by construction, so its row restates the headline. It is listed to make the
overlap explicit: no reviewed pull request fired exactly one class, so these rows are not
independent of each other and must not be compared as if they were.

## Sensitivity to the denominator

Excluding classes 5 and 6 raises precision slightly against counting them as false
positives. On this sample the choice is immaterial:

| rule | precision | 95% CI |
|---|---|---|
| 5 and 6 excluded (the contract's rule) | 6.9% | [1.9%, 16.7%] |
| 5 and 6 counted as false positives | 6.7% | [1.8%, 16.2%] |

Two tenths of a point. The published figure is not an artefact of that choice, and
anyone who thinks class 6 — flagged when no test changed at all — is plainly an
instrument failure rather than an undecidable can adopt the second row and lose nothing.

## What it means for the tool

The instrument measures what it measures exactly: whether a change edited test files
alongside source, deleted a test, or rewrote an existing expectation. Those are
mechanical facts about a diff and carry no inference. What is uncertain is the reading —
that the change retracted the evidence judging it — and in aggregate that reading held
about one time in fourteen, with a wide interval and no way to attribute it to a class.

That is enough for a list to spot-check across a repository's history, where a false
positive costs a glance. It is not enough for an accusation aimed at one author on one
pull request, where a false positive costs their afternoon and the tool's welcome. Hence
the default.
