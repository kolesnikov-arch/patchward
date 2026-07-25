# Pre-registered Contract — Study #1: how often do merged pull requests rewrite the tests that judge them?

**Date-stamped: 2026-07-25 (see this file's git history).**
**Status: NOT YET RUN. This document deliberately contains NO results — that is the
point.** The sampling frame, the instrument version, the review protocol, and the
reporting commitments are fixed *before* the data is collected, so they cannot be
fitted around the outcome. When the results publish, hold this document against them.

**Why this document exists at all:** the instrument under study is my own
([`patchward-check`](README.md)), and the finding will be used to argue that the
instrument is worth installing. That is a conflict of interest, stated plainly. The
only clean answer is to fix the rules in public before the number exists, and to
publish the number whichever way it comes out. This is the same discipline used for
the held-out evaluation in [RESULTS.md](https://github.com/kolesnikov-arch/patchward/blob/main/RESULTS.md),
against [that contract](https://github.com/kolesnikov-arch/patchward/blob/main/PREREGISTRATION.md).

---

## 1. What is being measured

**Primary question.** Among merged pull requests in public repositories, what fraction
modify both source and the tests covering it, and — within those — what fraction
*replace existing test expectations* rather than *add* new ones?

This is a **base rate**, not a comparison. No claim about AI-authored versus
human-authored code is made in this study; see §6.

**Secondary question, and the one that decides whether the instrument is honest.**
Of the pull requests the instrument flags at high severity, what fraction are, on
blind manual inspection, **legitimate engineering work** (intentional format change,
API rename, tightening a loose assertion, fixing a wrong test) rather than a change
that quietly moved its own goalposts?

That second number is the instrument's false-positive character. It is reported with
equal prominence, and it is the number most likely to be unflattering.

## 2. The instrument

- **Version:** `patchward-check` 0.1.0, pinned to a single git commit, recorded in the
  results artifact. If the instrument changes during the study, the study restarts.
- **Configuration:** default rules, no `--test-glob` additions, no per-repository
  tuning. Tuning the detector against the sample would make the sample worthless.
- **Definitions:** exactly as implemented in `patchward_check/detect.py` — high
  severity means `REWRITTEN_EXPECTATION`, `DELETED_TEST`, or `SUPPRESSED`.

## 3. Sampling frame (fixed before collection)

- **Population:** pull requests **merged** into the default branch of public
  repositories on GitHub, in the window **2026-01-01 .. 2026-06-30** inclusive.
- **Repository frame:** the top **50 per language group** by star count — **Python**,
  **JavaScript/TypeScript**, **Go** — for **150** repositories total, as reported by
  the GitHub search API on the collection date. (Per-group rather than a single
  pooled top-150, which would otherwise be dominated by whichever language has more
  mega-repositories.) Excluding:
  - repositories with fewer than 100 merged PRs in the window (too thin to sample);
  - repositories that are primarily documentation, awesome-lists, datasets, or course
    material (no test suite to speak of);
  - mirrors and forks.
  The resulting repository list is published verbatim with the results.
- **Sample:** **3,000** pull requests drawn uniformly at random from the frame with
  **seed 25**, stratified by language in proportion to available volume. The exact
  drawn PR list is published with the results.
- **Exclusions applied after drawing, and counted separately:** PRs whose diff
  exceeds 5,000 changed lines (vendored/generated bulk), PRs with no changed files
  reachable via the API, and PRs whose diff cannot be retrieved. These are reported as
  a disposition row, never silently dropped.
- **Unit of analysis:** one merged PR = one diff = one observation. Not per commit.
- **Enumeration method (stated because it can bias the population):** the GitHub
  search API returns at most 1,000 results per query and gives no warning when a
  query matches more. Each repository's window is therefore probed for its total
  and split in half recursively — down to single days if necessary — until every
  sub-window fits under that cap. Any sub-window still over the cap at one-day
  granularity is recorded in `population_meta.json` and reported with the results
  as a population shortfall. Listing by fixed months instead would have silently
  kept the earliest 1,000 merged PRs of each busy month: measured on a plumbing
  run before collection, that lost 47.5% of the population, biased toward
  earlier-created PRs.

Rate limits are an operational constraint, not a sampling criterion: if collection
cannot complete, the study reports the achieved n and the shortfall, and does not
substitute a different frame.

## 4. The blind review protocol (secondary question)

The failure mode this protocol exists to prevent is obvious: I inspect my own tool's
flags, decide most of them look correct, and publish a flattering precision number.

- **Sample for review:** 60 flagged + 60 unflagged PRs, drawn at random from the
  study sample with seed 25, **shuffled together and stripped of the tool's verdict**
  before review. The reviewer sees the diff and the PR title only.
  If fewer than 60 PRs are flagged at high severity in the whole sample, **all** of
  them are reviewed and matched with an equal number of unflagged ones; the reduced n
  is reported and the precision interval widens accordingly. The review sample is
  never topped up by drawing extra flagged PRs from outside the study sample.
- **Rubric, fixed now.** Each reviewed diff is classified into exactly one of:
  1. **Retracted evidence** — an expectation that previously held was changed or
     removed, and the PR gives no stated reason for it.
  2. **Justified expectation change** — same structural change, but the PR states an
     intentional behaviour/format/API change that requires it. **"States" means
     written down in the pull request**: its title, its description, or a comment or
     new test inside the diff that documents the intent explicitly. A reason the
     reviewer supplies from domain knowledge ("everyone knows ssh keys need a
     trailing newline") does **not** count — that is the reviewer resolving ambiguity
     in the instrument's favour, which is the exact failure this protocol exists to
     prevent. If the change is only justifiable by inference, it is category 1 or 5,
     never 2.
  3. **Nothing retracted** — tests changed, but no existing expectation was removed or
     altered. Covers both new coverage and mechanical scaffolding: a mock stub added so
     existing tests still compile, an import path moved, a helper renamed. (Named
     "nothing retracted" rather than "added coverage only" because scaffolding adds no
     coverage at all, and a label that claims otherwise would put a statement the data
     does not support into the results table. If scaffolding-only edits turn out to be
     a large share of this category, they are reported as their own row.)
  4. **Unrelated test change** — test edit not connected to the source change
     (lint, rename, flake fix, infrastructure).
  5. **Undecidable from the diff alone.**
  6. **No test change in this pull request** — the diff touches no test file at all.
- Categories 2, 3, 4 count as **false positives** when the tool flagged them at high
  severity. Category 5 is reported separately and never resolved in the tool's favour.
- Category 6 exists because roughly half the review sample is *unflagged* by
  construction, and many unflagged pull requests change no test at all. Without it
  those land in "undecidable", which would report a structural gap in the rubric as
  reviewer uncertainty. It is counted separately and is evidence in neither
  direction. A *flagged* pull request classified 6 is a contradiction — the
  instrument only fires on test edits — and is reported as such rather than folded
  into either column.
- **Second reviewer:** at least 25 of the 120 are independently classified by a second
  person; inter-rater disagreement is reported as a raw number. If no second reviewer
  can be found, that is disclosed and the precision figure is reported as
  single-rater — not quietly presented as if it were adjudicated.
- **The LLM arm, and how much human labelling is required.** An LLM may classify the
  review sample, and its labels are published as a separate, disclosed column. It is
  **never** the source of the headline precision figure and never counts as the second
  rater above: the instrument under test is itself automated, and validating it against
  another unvalidated automated judge — whose errors correlate with the instrument's,
  since both read the same surface features — produces a number nobody can interpret.
  The LLM arm therefore runs **after** the human labels are committed, so it cannot
  anchor them.
  - **At least 30 of the 120 must be human-classified.** If all 120 are, that is the
    primary precision figure. If only the subsample is, the primary figure is the
    human subsample — reported with its (wider) interval — and the LLM column is
    published beside it with the agreement rate between the two arms.
  - Agreement between the arms is reported as a finding in its own right: it is the
    first evidence on whether a model can stand in for a human reviewer in later
    studies of this kind. A high agreement does not retroactively promote the LLM
    column to primary in *this* study.

## 5. Reporting commitments

The results artifact must contain **all** of the following, whatever they say:

1. **Headline base rate** with an exact Clopper–Pearson 95% interval: PRs flagged at
   high severity / PRs analysed.
2. **Full disposition table**: analysed, excluded (by reason), clean, note, review,
   self-graded — summing to 3,000.
3. **Per-language breakdown**, including the languages where the path heuristics are
   least validated (see §7).
4. **The blind-review precision** with its interval, the full rubric tally, and the
   inter-rater disagreement count.
5. **Every high-severity finding class broken out separately.** A base rate driven
   entirely by `SUPPRESSED` is a different claim from one driven by
   `REWRITTEN_EXPECTATION`.
6. **The relationship between flag rate and diff size**, reported as a table by size
   bucket. If large diffs are flagged far more often, the headline is partly a proxy
   for "big PR" and that must be visible.
7. **At least three worked examples of false positives**, with diffs, chosen from the
   blind review — not the most flattering ones.
8. **The raw data**: repository list, drawn PR list, per-PR verdict, and a script that
   recomputes every figure from it.

## 6. What is NOT claimed by this study

- **No AI-versus-human comparison.** Author attribution on GitHub is unreliable —
  a large and unknowable share of "human" PRs are AI-assisted without any marker. A
  comparison built on that frame would be measuring labelling practice, not authorship.
  It is deliberately out of scope here and may be attempted as a separate,
  separately pre-registered study.
- **No claim that a flagged PR is wrong.** The instrument reports a structural
  property of a diff. Whether the change was correct is not measured, and the base
  rate must not be read as a defect rate.
- **No claim about predictive power.** Whether flagged changes are more likely to be
  defective requires linking to downstream outcomes (reverts, follow-up fixes,
  incident data). Not in this study.
- **No claim of representativeness beyond the frame.** Top-starred repositories in
  three languages are not "software." Small teams, private codebases, and less
  mature projects may differ in either direction.

## 7. Anticipated objections — answered before the result

**"Your test-file detection is just path conventions, so the base rate is an artefact
of your regexes."** Partly fair, and it is why §5.3 requires a per-language breakdown
and §4 requires blind review of *unflagged* PRs too — the latter is what would surface
systematic misses. The detector's path rules are best validated on Python and least on
Go; that ordering is stated now, before the numbers, so it cannot become a
post-hoc excuse.

**"You'll tune the detector once you see the data."** The instrument is pinned to a
commit (§2) and the study restarts if it changes. Any rule change prompted by this
data lands *after* publication, in a version whose number is measured on a fresh
sample.

**"A high base rate just means everyone does this, so it's fine."** That would be a
legitimate reading and the study is designed to permit it. If the base rate is high
and the blind review says most flags are justified changes, the honest conclusion is
that the signal is weak as a standalone alarm — and that will be written in those
words.

**"You chose the window and the frame to get a number you liked."** The frame is fixed
here, before collection, and the repository list and drawn PR list publish with the
results so anyone can redraw.

## 8. Freeze discipline

- This file is committed **before** any collection begins. Its git history is the
  timestamp; there is no other claim of priority.
- The instrument commit hash, the collection start time, and the collection end time
  are recorded in the results artifact.
- No PR is re-fetched to get a different verdict. No repository is added or removed
  after the draw. If a bug in the collector is found mid-run, the run is discarded and
  restarted from the same seed, and the discarded run is disclosed.
- **The study publishes whatever it finds**, including a null or unflattering result.
  A base rate near zero would mean the instrument fires too rarely to matter; a
  precision near zero would mean it fires too loosely to trust. Both outcomes are
  publishable and both will be published.

---

*Contract for Study #1, `patchward-check`. No results exist at the time of writing.*
