# Held-out results — Evaluation #1 (2026-07-05)

**🇺🇸 English | [🇨🇳 简体中文](RESULTS_zh.md)**

**On a frozen, pre-registered, held-out set of 50 SWE-bench Lite tasks, the same
model silently shipped 17/50 wrong fixes when ungated — and 0/50 when an
independent verdict layer decided what ships.**

> Written up, with Studies #1 and #3, in a preprint:
> [doi.org/10.5281/zenodo.21721312](https://doi.org/10.5281/zenodo.21721312)

The scoring rules for this evaluation were published **before the result existed**:
[Pre-registered Scoring Contract](PREREGISTRATION.md) (committed 2026-07-03; the run
completed 2026-07-05). Every reporting commitment in that contract (§3) is delivered
below. Every number can be recomputed from the raw artifacts in
[`evaluation-artifacts/`](evaluation-artifacts/).

---

## 1. Headline (counts first)

| | Ungated arm | Gated arm |
|---|---|---|
| **Silently shipped wrong fixes** | **17 / 50 (34.0%)** | **0 / 50 (0.0%)** |
| 95% CI (Clopper-Pearson, exact) | [21.2%, 48.8%] | [0.0%, 7.1%] |

The intervals do not overlap; Fisher exact (two-sided) **p ≈ 3.0×10⁻⁶**.

Same tasks, same proposer model in both arms. The only difference is process:
ungated, every patch the model produces ships silently; gated, an independent verdict
layer renders **Verified / Needs review / Blocked**, and only *Verified* ships
without a human in the loop.

One number to hold next to the headline, disclosed up front: the gated arm issued
**zero Verified verdicts** on this set — in this configuration it never vouched
confidently at all (§4 explains why, and why that is conservatism rather than a
trick; §2's yield row is the anti-trivialization check the contract commits to).

## 2. Full disposition (contract §3.3)

| | Ungated | Gated |
|---|---|---|
| Verified (vouched & shipped) | n/a | **0** |
| Shipped silently — correct / wrong | 33 / **17** | n/a |
| Needs review — correct / wrong | n/a | 24 / 14 |
| Blocked — correct-block / false-reject | n/a | 7 / 5 |
| **Total** | **50** | **50** |
| **Delivered-correct yield** | **33** (all silent) | **24** (every one flagged) |

**Sensitivity row (contract §3.4, the pessimistic contract):** count every wrong
*Needs review* patch against the gated arm as if the flag were ignored and it merged
anyway: **14/50 (28.0%, CI [16.2%, 42.5%])** vs. the ungated arm's 17/50 (34.0%).
Even a reader who fully distrusts the flag channel scores the gated arm at fewer
wrong ships — and every one of those arrived flagged, versus 17 silent merges.

**The honest cost:** the gated arm delivered 24 correct fixes to the ungated arm's
33. Five of that nine-fix gap are characterized false-rejects (§5) — recoverable
instrument work, not a law of nature.

## 3. What the blocks actually caught

Seven blocks were confirmed correct by the hidden reference tests — the layer
actively refused fixes that were in fact wrong, through more than one mechanism:

- **`sympy__sympy-22840`** — the gated arm's candidate fix would have broken
  **36 existing tests**; the isolated verification run caught the regression and
  blocked it. The ungated arm shipped its own wrong variant of the fix silently.
- **`sympy__sympy-16503`** — the marquee case. The ungated arm produced a wrong fix
  *and rewrote the existing test to expect its own wrong output* — the failure mode
  where an agent doesn't just err but hides the error. The gated arm's patch was
  confined to declared source scope (it cannot edit tests), and its own wrong fix
  was caught and blocked by the independent acceptance check. Originals preserved in
  [`evaluation-artifacts/test_touching_originals/`](evaluation-artifacts/test_touching_originals/).
- Five more confirmed correct-blocks (`pydata__xarray-4248`,
  `sphinx-doc__sphinx-8282`, `sphinx-doc__sphinx-8801`, `sympy__sympy-15678`,
  `pylint-dev__pylint-7993`), including three where the ungated arm *out-solved* the
  gated one on the same task — and the gated arm still correctly blocked its own
  wrong attempt instead of shipping it.

And the cleanest paired illustration of the whole thesis, **`django__django-13321`**:
both arms produced a near-identical incomplete fix (same file, 719 vs 720
characters). The ungated arm shipped it silently — a false-accept. The gated arm
delivered the same fix flagged *Needs review — could not verify*. Identical
capability; the entire difference is accountability.

## 4. Confident-vouch rate: 0/50 (contract §3.7 — reported, off-headline)

In this benchmark configuration the layer's only independent oracle is an acceptance
test synthesized from the issue text alone (authored blind to the fix — the
leak-safety requirement). Most real issues underdetermine the hidden reference
tests, so verification honestly returns "could not fully verify" and the verdict
stays *Needs review*. That is the disclosed trade of a thin-but-independent oracle:
it costs vouches, not trust — no wrong fix gained a confident verdict.

As pre-registered (§6): the vouch rate is not the pitch, and we don't sell it. In a
real deployment the layer would run the client's own pre-existing test suite — a
much richer oracle that is *still independent of the proposing agent* — which
upgrades verdicts from *Needs review* toward *Verified* without admitting the
silent-failure mode measured here. That upgrade path is roadmap, not part of this
result.

## 5. False-rejects — all five, with root causes (contract §3.6)

Recall cost, zero trust cost (a block is never a silent wrong ship). Two distinct,
characterized classes:

1. **Acceptance-test author produced environment-incompatible test code** (2):
   `django__django-12708` (an import that doesn't exist in that Django version),
   `django__django-12915` (an asyncio API newer than the instance's Python). The
   fix-blind test crashed at scaffolding, which scored as a failed check and blocked
   a gold-correct fix.
2. **The regression check over-fired** (3): `django__django-16527`,
   `django__django-17087`, `sympy__sympy-13971` — it flagged regressions the gold
   harness does not confirm. `django__django-17087` is the smoking gun: both arms
   produced a **byte-identical** patch; the ungated copy resolved, the gated copy was
   blocked. The same check also under-fired once (`sphinx-doc__sphinx-7738`: a real
   test break it missed — masked there because the verdict was already *Needs
   review*, but a latent risk we are naming ourselves).

Both classes are instrument calibration work, scheduled as the next evaluation's
delta — on a fresh held-out set, against these same rules.

## 6. Run integrity (contract §3.6, §5)

- **Selection:** frozen seeded script (seed=50) over SWE-bench Lite; 63 instances
  ever used for development/tuning excluded; **zero overlap** — reproducible from
  [`evaluation-artifacts/selection/`](evaluation-artifacts/selection/). Repos:
  django 23, sympy 16, sphinx 6, xarray 3, pylint 2.
- **Instrument freeze:** pinned at commit `759f3f5` before the first run; HEAD did
  not move during the run.
- **Infrastructure-only fix log (1):** commit `b5e950b` — stdin text-encoding bug in
  the *ungated* arm's model invocation (Windows locale codec choked on a zero-width
  space in one issue text, so the model was never called at all). Call-or-no-call
  only; cannot alter any verdict. Both affected runs re-ran post-fix; one of them
  turned out **in the ungated arm's favor** (an apparent miss became a shipped
  correct fix).
- **Flake policy:** non-completions (wall-clock timeout with the model still
  iterating: 3× ungated; one crashed role call: 1× gated) were re-run once at the
  frozen timeout, every run recorded, verdicts never re-rolled. Notably the *gated*
  arm's one flake re-ran to a *Needs review — correct* — the re-run budget cut a
  would-be false-reject, i.e. it worked against our headline's favor too.
- **Test-touching predictions:** handled by the source-only rule pre-registered
  before the result (details in
  [`evaluation-artifacts/README.md`](evaluation-artifacts/README.md)).

## 7. Limitations

The standing list is in
[Current Scope & Limitations](CURRENT_SCOPE_AND_LIMITATIONS.md). The ones that bound
*this* result: Python repositories only; one benchmark (SWE-bench Lite); n=50 —
hence exact CIs and counts-first reporting; the oracle is thin (see §4); a benchmark
false-accept is a proxy for production risk, not the thing itself; and the proposer
model has plausibly seen these repositories in training — which is arm-symmetric and
therefore shifts absolute solve rates, not the gated-vs-ungated comparison. No
capability claim is made anywhere: **the layer does not make the model smarter; it
makes the model's output accountable.**

## 8. Verify it

```bash
git clone https://github.com/kolesnikov-arch/patchward && cd patchward/evaluation-artifacts
python verify_counts.py          # recompute counts, CIs, Fisher from raw reports
# full re-scoring in Docker: see evaluation-artifacts/README.md (3 commands)
```

*This is Evaluation #1. The rules stay fixed; the next evaluation reports a delta
against them — including whether the five false-rejects above were in fact
recovered.*
