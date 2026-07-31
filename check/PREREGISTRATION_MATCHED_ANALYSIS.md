# Pre-registered Contract — Study #1, Analysis 2: does the repository-class difference survive adjustment for change size?

**Date-stamped: 2026-07-31 (see this file's git history).**
**Status: NOT YET RUN. This document contains no adjusted estimate — that is the point.**

This is a **secondary analysis of data already collected** under the Study #1 contract
([PREREGISTRATION_PR_STUDY.md](PREREGISTRATION_PR_STUDY.md)) and already published
([study-artifacts/RESULTS.md](study-artifacts/RESULTS.md)). The data therefore exists
before its analysis plan, which is a weaker guarantee than Study #1 had, and the
weakness is stated here rather than glossed:

**What is already known to the analyst** (published, and unavoidable):
- the unadjusted comparison — AI-adjacent repositories **25.9%** (408/1,575) versus
  other repositories **22.0%** (299/1,358);
- the change-size gradient in the pooled data — **4.1%** at 0–20 changed lines rising
  to **59.5%** at 2,001–5,000;
- per-language rates, all overlapping.

**What is not known to anyone at the time of this commit:** any size-adjusted,
language-adjusted, or cluster-corrected estimate. No such figure has been computed by
the author or by any assistant. That is the specific thing this document fixes the
rules for, and the git timestamp is the only evidence that matters.

---

## 1. The question

The unadjusted difference is 3.9 points. Change size is a strong predictor of the
outcome and plausibly differs between the two repository classes. **Does the
difference survive adjustment for change size, and does it survive treating the
repository, not the pull request, as the unit that repeats?**

The expected answer is that it does not. Publishing the plan first is what makes that
answer worth anything.

## 2. What is being compared — definitions carried over, not redefined

- **Unit of observation:** the merged pull request; the 2,933 analysed PRs of Study #1.
  No re-collection, no re-drawing, no window change.
- **Outcome:** the high-severity flag exactly as defined and produced by the pinned
  instrument (`patchward-check`, commit `d2f14f4`) — 707/2,933 in the published run.
  The instrument is not re-run and not re-tuned.
- **Exposure (repository class):** the classification already recorded in
  `study-artifacts/summary.json` → `frame_composition.pattern`, applied to repository
  description and topics, **verbatim**. No repository is re-classified, added, or
  dropped; ambiguous cases are not adjudicated by hand. The frame is 150 repositories
  (147 with drawn PRs), 64 AI-adjacent by that pattern.
- **Stratifier:** `changed_lines` from `results.jsonl`, in the five bins already
  published: 0–20, 21–100, 101–500, 501–2,000, 2,001–5,000.
  **Common-support rule, fixed now:** a bin enters the primary analysis only if it
  holds at least 30 pull requests in **each** class. Bins failing that are excluded,
  and the report states which, how many pull requests they hold, and what share of the
  sample the analysis therefore covers. The estimate is a claim about the size range
  where both classes are actually present; outside it the data cannot answer, and this
  analysis does not extrapolate.

  *Why not merge thin bins into their neighbours,* which was this document's rule until
  it was tested: merging cascades. One thin cell pulls in its neighbour, the pair is
  thin against the next, and five strata collapse into two — leaving inside the wide
  strata exactly the size imbalance the adjustment exists to remove. On synthetic data
  built with **no class effect by construction**, the merging rule returned +5.53 pp
  with a 95% interval excluding zero; the common-support rule returned +2.99 pp with
  the interval covering zero. The rule was therefore changed **before this contract was
  committed and before any run against the real artifacts** (§8). The merging result is
  still computed and published as a contrast (§4.6), so the reader can see the
  difference the choice makes.
- **Cluster:** the repository. 147 clusters; the three largest contribute 5.97%, 5.07%
  and 4.87% of drawn PRs.

## 3. Primary estimand — one, chosen before the data speaks

**Directly standardized rate difference:** the flag rate of each class, standardized to
the change-size distribution of all 2,933 analysed PRs, reported as
`AI-adjacent minus other` in percentage points.

**Interval:** 95% cluster bootstrap over repositories — resample the 147 repositories
with replacement, take all PRs of each drawn repository, recompute the standardized
difference; 2,000 resamples; `seed = 2026`; percentile interval. Clustering is
corrected because pull requests within a repository share a test culture, which the
published `z = 2.45` ignores.

Counts first: both classes' raw and standardized rates, with denominators, before any
difference is stated.

## 4. Secondary analyses — labelled secondary, reported in full

1. **Cochran–Mantel–Haenszel** common odds ratio with a Robins–Breslow–Greenland
   interval, computed over **all five bins** — MH is designed for sparse strata, so it
   is the natural check on whether the common-support restriction changed the answer.
2. **Language group** (go / js-ts / python) as a second stratifier, then jointly with
   size, subject to the same min-cell rule.
3. **Concentration sensitivity:** repeat the primary with the three most heavily drawn
   repositories excluded.
4. **Repository as the unit:** flag proportion per repository, compared between classes
   by Wilcoxon rank-sum, repositories with fewer than 10 drawn PRs excluded. This
   answers a different question — whether *repositories* differ, rather than PRs — and
   it is **unadjusted for change size by construction.** Since change size is the
   dominant predictor in this data, a difference here is expected whether or not the
   primary analysis finds one, and it must not be quoted as support for the primary
   question. Reported because leaving it out would look like a choice.
5. **Descriptive, not inferential:** the change-size distribution of each class,
   published as a table, because it is the mechanism the primary analysis adjusts for.
6. **Contrast with the rejected merging rule** (§2): the same standardization computed
   over cascaded strata, published so the effect of the strata choice is visible rather
   than argued.

No other cut is reported. If an unplanned analysis is run, it is labelled
**exploratory** in the write-up and never appears in a summary sentence.

## 5. Reporting commitments

- **Published whichever way it comes out**, including — most likely — "the unadjusted
  difference does not survive adjustment for change size."
- Written in those words, in the same paragraph as the unadjusted 3.9 points, so no
  reader can carry away only the flattering half.
- Published as an **amendment to Study #1** (`study-artifacts/RESULTS.md` plus this
  contract), **not as a new study** and not as a new headline. It answers a question
  the original left open; it is not a fourth result.
- The analysis script is committed together with this document, before it is run, and
  recomputes every reported figure from the published artifacts. If a bug is found
  after the run, the fix is committed with a note and **the whole analysis is re-run**;
  both runs stay in the history.
- Run once. There is no second look with different bins.

## 6. What is NOT claimed

- **This is not a claim about AI-written code.** The exposure is a property of the
  *repository* — its description and topics mention AI — not of the pull request's
  author. Study #1 §6 rules out author attribution as unreliable, and nothing here
  changes that. A difference, if one survives, is a difference between *communities of
  practice*, not between human and machine authorship.
- **This is not a defect rate.** The instrument reports a structural property of a
  diff — source changed and an existing test expectation replaced — at a measured
  precision of **6.9%** (CI [1.9, 16.7]). The honest reading of any surviving
  difference is "in these repositories, changes more often arrive with their own test
  expectations rewritten", never "these repositories ship more broken code".
- **The primary threat to validity, stated before the number:** precision is estimated
  from 120 reviewed cards containing only **4 true positives**, which is far too few to
  estimate precision *per class*. If the instrument's precision differs between AI-
  adjacent and other repositories, an adjusted difference in flag rate does not
  transfer to a difference in the underlying practice. This cannot be resolved with the
  current review sample; it is a limitation, not a caveat to be buried.
- **No causal claim.** Adjustment for change size removes one confounder that was named
  in advance. Repository age, team size, review culture, CI maturity and monorepo
  structure are not measured here.
- **No representativeness beyond the frame** — top-starred repositories in three
  languages, merged PRs, 2026-01-01 to 2026-06-30.

## 7. Anticipated objections — answered before the result

**"You already saw the marginals, so this is not a pre-registration."** Correct, and
§0 says so. It is a pre-registered *analysis plan for pre-existing data*: the estimand,
the strata, the interval method, the seed and the publication commitment are fixed
before any adjusted figure exists. That is weaker than Study #1 and stronger than the
usual practice of reporting whichever adjustment looked best.

**"You will keep adjusting until the difference disappears / survives."** One primary
estimand, one seed, one run, script committed first. Everything else is labelled
secondary or exploratory in advance.

**"Adjusting for change size is itself a choice that kills the effect."** It is, and
it is defended on grounds that predate the data: the size gradient spans 4.1% to
59.5%, an order of magnitude larger than the 3.9-point difference under examination.
Both the adjusted and the unadjusted figures are published side by side, so a reader
who disagrees with the adjustment can use the raw one.

**"AI-adjacent by description and topics is a crude classifier."** Agreed. It is the
one already frozen and published in Study #1; changing it now to something better
would be exactly the kind of post-hoc refinement this document exists to prevent. A
better classifier is a future study with its own frame.

## 8. Freeze discipline

- No new data collection; no instrument change; no re-classification.
- This document and `study/matched_analysis.py` are committed **before** the script is
  executed for the first time on the real artifacts.
- Smoke-testing on synthetic data is permitted and expected; any run against
  `study-artifacts/` before this commit would void the contract, and none has occurred.
  The generator — 150 repositories, flag probability a function of change size
  **alone**, AI-adjacent repositories shifted to larger changes — ships as
  `study/test_matched_analysis.py` and is run with
  `python study/test_matched_analysis.py`. Its four assertions are the ones that caught
  the merging rule, and they fail if the strata logic regresses. Fixing a rule because a synthetic test
  showed it produces a false positive is legitimate; changing anything after seeing the
  real artifacts is not, and the git history is what separates the two.
- If any of the above is violated, the violation is written into the results document,
  the way the six discarded labelling sessions are recorded in
  `../selfreport/LABELLING_LOG.md`.
