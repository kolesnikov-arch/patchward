# Study #1 results — how often do merged pull requests rewrite the tests that judge them?

**Run date: 2026-07-26. Instrument: `patchward-check` @ `d2f14f4`.**
Reported against [the pre-registered contract](PREREGISTRATION_PR_STUDY.md), committed before collection began.

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

| | count |
|---|---|
| Flagged & confirmed *retracted evidence* | 4 |
| Flagged & judged legitimate (**false positive**) | 54 |
| Flagged & undecidable from the diff | 0 |
| **Not** flagged but retracted evidence (**missed**) | 0 |
| No test change in the pull request at all | 41 |
| Flagged although no test changed (contradiction — a bug) | 2 |

**Precision: 6.9%** [1.9%, 16.7%]

Undecidable cases are never resolved in the instrument's favour (contract §4).

**Misses: 0 of 60 unflagged cards — and this design had almost no power to find one.** At the underlying rate derived below (1.7%), 60 unflagged pull requests are expected to contain about 1.0 genuine case(s), and only 19 of them touched a test file at all. An instrument with **zero** recall would still have produced zero misses here with probability 37%. The 95% upper bound on the miss rate among unflagged pull requests is 5% (rule of three).

**So recall is not established.** "It does not overlook" is not a claim these data can carry, and any use of this instrument as a high-recall sieve rests on a number that was never measured. What the data do support is the narrower finding that it over-fires.

**What the two numbers mean together.** The instrument fires on 24.1% of merged pull requests; about 6.9% of those firings are real. The implied underlying rate — merged changes that quietly retract the evidence that judged them — is **1.7%** as a point estimate, and propagating both intervals naively gives roughly [0.4%, 4.3%]. Anyone quoting 24.1% on its own is quoting the alarm, not the fire.

**These labels are LLM-rated, not human-rated** (contract §4, §6). The judge and the instrument read the same diff, so their errors correlate, which biases precision *upward*. Discount accordingly; the base rate above carries no such caveat. All 120 cards, both passes and their reasons ship with these results so the labels can be re-rated.

Two independent passes over the same 120 cards agreed on **105** and differed on **15** (87.5% stable). This measures label stability, not agreement between people — the study has no human arm and does not claim one.

## 7. Reproducing this

```bash
python -m study verify
```

Recomputes every figure above from `results.jsonl` and fails loudly on any mismatch. The repository frame, the drawn PR list, and the per-PR verdicts are all in `study-artifacts/`.
