# Study #1 results — how often do merged pull requests rewrite the tests that judge them?

**Run date: 2026-07-26. Instrument: `patchward-check` @ `d2f14f4`.**
Reported against [the pre-registered contract](../PREREGISTRATION_PR_STUDY.md), committed before collection began.

## 1. Disposition first (contract §5.2)

| | count |
|---|---|
| Drawn | **3000** |
| Analysed | 2933 |
| Excluded | 67 |
| &nbsp;&nbsp;— diff-unavailable | 19 |
| &nbsp;&nbsp;— empty-diff | 8 |
| &nbsp;&nbsp;— oversize:5502 | 1 |
| &nbsp;&nbsp;— oversize:7527 | 1 |
| &nbsp;&nbsp;— oversize:12968 | 1 |
| &nbsp;&nbsp;— oversize:9679 | 1 |
| &nbsp;&nbsp;— oversize:10008 | 1 |
| &nbsp;&nbsp;— oversize:5023 | 1 |
| &nbsp;&nbsp;— oversize:10415 | 1 |
| &nbsp;&nbsp;— oversize:13876 | 1 |
| &nbsp;&nbsp;— oversize:12973 | 1 |
| &nbsp;&nbsp;— oversize:22069 | 1 |
| &nbsp;&nbsp;— oversize:8303 | 1 |
| &nbsp;&nbsp;— oversize:15345 | 1 |
| &nbsp;&nbsp;— oversize:10537 | 1 |
| &nbsp;&nbsp;— oversize:5286 | 1 |
| &nbsp;&nbsp;— oversize:42378 | 1 |
| &nbsp;&nbsp;— oversize:28207 | 1 |
| &nbsp;&nbsp;— oversize:5021 | 1 |
| &nbsp;&nbsp;— oversize:17360 | 1 |
| &nbsp;&nbsp;— oversize:7505 | 1 |
| &nbsp;&nbsp;— oversize:8804 | 1 |
| &nbsp;&nbsp;— oversize:12986 | 1 |
| &nbsp;&nbsp;— oversize:14834 | 1 |
| &nbsp;&nbsp;— oversize:15245 | 1 |
| &nbsp;&nbsp;— oversize:5361 | 1 |
| &nbsp;&nbsp;— oversize:5621 | 1 |
| &nbsp;&nbsp;— oversize:6733 | 1 |
| &nbsp;&nbsp;— oversize:8824 | 1 |
| &nbsp;&nbsp;— oversize:18289 | 1 |
| &nbsp;&nbsp;— oversize:5499 | 1 |
| &nbsp;&nbsp;— oversize:22044 | 1 |
| &nbsp;&nbsp;— oversize:5794 | 1 |
| &nbsp;&nbsp;— oversize:5337 | 1 |
| &nbsp;&nbsp;— oversize:7423 | 1 |
| &nbsp;&nbsp;— oversize:6019 | 1 |
| &nbsp;&nbsp;— oversize:7803 | 1 |
| &nbsp;&nbsp;— oversize:5535 | 1 |
| &nbsp;&nbsp;— oversize:11090 | 1 |
| &nbsp;&nbsp;— oversize:10834 | 1 |
| &nbsp;&nbsp;— oversize:5904 | 1 |
| &nbsp;&nbsp;— oversize:11975 | 1 |

Excluded + analysed = 3000; drawn = 3000. These must be equal.

## 2. Headline base rate

> Of **2933** analysed merged pull requests, **707** (24.1%) were flagged at high severity — the change replaced, deleted, or suppressed an existing test expectation.

95% CI (Clopper-Pearson, exact): **[22.6%, 25.7%]**  
Wilson, for comparison: [22.6%, 25.7%]

**This is not a defect rate.** It counts a structural property of a diff. Whether any of these changes was wrong is not measured here (contract §6).

## 3. Which rule fired (contract §5.5)

| finding | count | share of analysed |
|---|---|---|
| `REWRITTEN_EXPECTATION` | 667 | 22.7% |
| `DELETED_TEST` | 229 | 7.8% |
| `SUPPRESSED` | 37 | 1.3% |

## 4. By language group (contract §5.3)

| group | analysed | flagged | rate | 95% CI |
|---|---|---|---|---|
| go | 523 | 124 | 23.7% | [20.1%, 27.6%] |
| js-ts | 1234 | 304 | 24.6% | [22.3%, 27.1%] |
| python | 1176 | 279 | 23.7% | [21.3%, 26.3%] |

> Path heuristics are best validated on Python and least on Go — stated in the contract (§7) before these numbers existed.

## 5. Flag rate against diff size (contract §5.6)

| changed lines | analysed | flagged | rate |
|---|---|---|---|
| 0-20 | 886 | 36 | 4.1% |
| 21-100 | 828 | 170 | 20.5% |
| 101-500 | 823 | 284 | 34.5% |
| 501-2000 | 317 | 170 | 53.6% |
| 2001-5000 | 79 | 47 | 59.5% |

> If the rate climbs steeply with size, the headline is partly a proxy for *large pull request* and should be read that way.

## 5b. What the frame is actually made of (disclosure)

The contract fixes the frame as *top 50 per language group by stars*. In this window that means **64 of 150 repositories** are AI or agent projects by the published keyword pattern, and because those repositories are unusually busy they carry **54% of the merged-PR volume** the sample is drawn from.

| group | repositories | AI-adjacent |
|---|---|---|
| go | 50 | 12 |
| js-ts | 50 | 20 |
| python | 50 | 32 |

The classifier is a keyword pattern, published here so it can be disputed, and it **over-counts** — a repository whose description merely mentions a model or a chat feature lands in the AI bucket:

```
\b(ai|a\.i\.|llm|llms|gpt|agent|agents|agentic|chatbot|copilot|prompt|prompts|rag|inference|embedding|embeddings|transformer|transformers|diffusion|openai|anthropic|claude|gemini|deepseek|qwen|llama|mistral|ollama|vllm|langchain|mcp|assistant|coding-agent)\b
```

This is a property of the *repository*, not of who wrote any pull request. It is not the AI-versus-human comparison the contract declines (§6): that needs author attribution, which is unreliable. This cut was added after the frame was built and **before any diff was fetched or scored**, so it cannot have been chosen to flatter a verdict that did not exist yet.

| repository class | analysed | flagged | rate |
|---|---|---|---|
| ai-adjacent | 1575 | 408 | 25.9% |
| other | 1358 | 299 | 22.0% |

> If these two rates differ materially, the headline is partly a statement about which repositories dominate the frame, and should be read that way.

**They do not, once change size is held fixed — see [§8](#8-analysis-2-does-the-repository-class-difference-survive-adjustment).** The 3.9-point gap above is unadjusted, and it is the gap that section was written to test.

**Concentration.** The draw is proportional to volume, as the contract specifies, so the sample is not spread evenly: 3000 pull requests come from 147 repositories, and the busiest ten supply **40%** of them.

| repository | drawn | share |
|---|---|---|
| openclaw/openclaw | 179 | 6.0% |
| getsentry/sentry | 152 | 5.1% |
| microsoft/vscode | 146 | 4.9% |
| NousResearch/hermes-agent | 128 | 4.3% |
| home-assistant/core | 119 | 4.0% |
| grafana/grafana | 113 | 3.8% |
| n8n-io/n8n | 105 | 3.5% |
| cockroachdb/cockroach | 93 | 3.1% |
| vllm-project/vllm | 80 | 2.7% |
| BerriAI/litellm | 77 | 2.6% |

## 6. Blind review — the false-positive number (contract §4, §5.4)

Reviewed blind: **120** pull requests (flagged and unflagged, shuffled, verdicts hidden).

**Both passes are reported side by side.** Neither is adjudicated into the other, and the
figures below are not merged; where they differ, the difference is the finding.

| | pass 1 | pass 2 |
|---|---:|---:|
| Flagged & confirmed *retracted evidence* | 4 | 4 |
| Flagged & judged legitimate (**false positive**) | 54 | 53 |
| Flagged & undecidable from the diff | 0 | 2 |
| **Not** flagged but retracted evidence (**missed**) | 0 | **1** |
| No test change in the pull request at all | 41 | 41 |
| Flagged although no test changed (contradiction — a bug) | 2 | 1 |

**Precision: 6.9%** [1.9%, 16.7%] under pass 1; **7.0%** [1.9%, 17.0%] under pass 2.

Undecidable cases are never resolved in the instrument's favour (contract §4).

**What the false positives are made of**, since the repair below depends on the split
(rubric categories, contract §4; flagged cards only):

| | pass 1 | pass 2 |
|---|---:|---:|
| 1 — retracted evidence | 4 | 4 |
| 2 — justified, and the pull request says so | 28 | 21 |
| 3 — nothing retracted (the tool was simply wrong) | 26 | 32 |
| 5 — undecidable | 0 | 2 |
| 6 — no test change (contradiction) | 2 | 1 |

Reading the pull-request description and downgrading category 2 would take precision to
**13.3%** under pass 1 and **11.1%** under pass 2 — double, and still not an instrument
you would leave switched on. It is not applied here: the contract forbids tuning on the
data that produced the verdict (§7).

**Misses: 0 of 60 unflagged cards under pass 1, 1 under pass 2 — and this design had
almost no power to find either.** The passes disagree on the one card: `R052`
([vercel/next.js#89147](https://github.com/vercel/next.js/pull/89147)), a generated build
manifest that moves a test out of `passed`. Pass 2 read that as a retracted expectation;
pass 1 called it an unrelated test change and flagged it in its own note for re-rating.
It is reported here rather than resolved, because resolving it means choosing the pass
whose answer is more convenient. At the underlying rate derived below (1.7%), 60 unflagged
pull requests are expected to contain about 1.0 genuine case(s), and only 19 of them
touched a test file at all. An instrument with **zero** recall would still have produced
zero misses here with probability 37%. The 95% upper bound on the miss rate among
unflagged pull requests is 5% (rule of three).

**So recall is not established.** "It does not overlook" is not a claim these data can carry, and any use of this instrument as a high-recall sieve rests on a number that was never measured. What the data do support is the narrower finding that it over-fires.

**What the two numbers mean together.** The instrument fires on 24.1% of merged pull requests; about 6.9% of those firings are real. The implied underlying rate — merged changes that quietly retract the evidence that judged them — is **1.7%** as a point estimate, and propagating both intervals naively gives roughly [0.4%, 4.3%]. Anyone quoting 24.1% on its own is quoting the alarm, not the fire.

**These labels are LLM-rated, not human-rated** (contract §4, §6). The judge and the instrument read the same diff, so their errors correlate, which biases precision *upward*. Discount accordingly; the base rate above carries no such caveat. All 120 cards, both passes and their reasons ship with these results so the labels can be re-rated.

Two independent passes over the same 120 cards agreed on **105** and differed on **15** (87.5% stable). This measures label stability, not agreement between people — the study has no human arm and does not claim one.

## 7. Reproducing this

```bash
python -m study verify
```

Recomputes every figure above from `results.jsonl` and fails loudly on any mismatch. The repository frame, the drawn PR list, and the per-PR verdicts are all in `study-artifacts/`.

---

## 8. Analysis 2: does the repository-class difference survive adjustment?

**Run date: 2026-07-31.** Contract: [PREREGISTRATION_MATCHED_ANALYSIS.md](../PREREGISTRATION_MATCHED_ANALYSIS.md) and the code that produces every figure below were committed in `e7308fb`, **before this analysis was run for the first time on these artifacts**. No new data was collected; nothing was re-classified or re-scored.

§5b left one question open: the 3.9-point gap between AI-adjacent repositories (25.9%) and the rest (22.0%). Change size predicts the outcome far more strongly than anything else in this data — from 4.1% at 0–20 changed lines to 59.5% at 2,001–5,000 (§5) — and the two classes do not merge changes of the same size.

### The answer

**Standardized to the pooled change-size distribution: −0.15 pp, 95% cluster bootstrap CI [−4.90, +4.59].** AI-adjacent 23.95%, other 24.09%. **The unadjusted difference does not survive adjustment for change size.**

The mechanism is visible directly: median changed lines is **87** in AI-adjacent repositories against **48** elsewhere. Within each size stratum the two classes behave the same way.

| changed lines | AI-adjacent | rate | other | rate |
|---|---|---|---|---|
| 0–20 | 12 / 403 | 3.0% | 24 / 483 | 5.0% |
| 21–100 | 87 / 429 | 20.3% | 83 / 399 | 20.8% |
| 101–500 | 173 / 505 | 34.3% | 111 / 318 | 34.9% |
| 501–2,000 | 105 / 189 | 55.6% | 65 / 128 | 50.8% |
| 2,001–5,000 | 31 / 49 | 63.3% | 16 / 30 | 53.3% |

Every stratum carried at least 30 pull requests in both classes, so the contract's common-support restriction never bound: the estimate covers **100%** of the analysed sample. The strata rule the contract rejected (§2 of the contract) returns the same −0.15 pp here, because no merge fires on this data — the rule change could not have manufactured this answer.

### Secondary analyses (contract §4)

| analysis | result |
|---|---|
| Mantel–Haenszel common odds ratio, all strata | **0.989**, 95% CI [0.820, 1.192] |
| Excluding the three most heavily drawn repositories | +0.16 pp |
| Per language, standardized (smaller n, unstable) | go −2.7 pp · js-ts +4.46 pp · python −5.27 pp |
| Repository as the unit, **unadjusted by construction** | median flag proportion 24.2% vs 18.8%; Mann–Whitney *p* = 0.26 |

The per-language figures scatter in both directions with no consistent sign, which is what a null looks like at these sample sizes. The repository-level comparison is unadjusted for change size on purpose — it answers whether *repositories* differ, is expected to track the raw gap, and must not be read as support for the primary question; it is reported because omitting it would be a choice.

### What this does and does not say

It says that in this frame, once you compare changes of similar size, repositories that describe themselves as AI or agent projects replace existing test expectations at the same rate as everything else. The visible gap was a statement about change size, not about the repositories.

It does not say anything about correctness. The instrument reports a structural property of a diff at 6.9% precision (§6); the honest reading is about a practice, not a defect rate. And with only four confirmed true positives in the blind review, precision **per class** cannot be estimated at all — if the instrument's precision differed between the two classes, no comparison of flag rates would transfer to the underlying practice. That limit was stated in the contract before the number existed and does not go away because the number came out null.

```bash
python -m study.matched_analysis      # writes study-artifacts/matched_analysis.json
python study/test_matched_analysis.py # the strata rule, on data with no effect in it
```
