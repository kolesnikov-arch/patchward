"""Study #1, Analysis 2 — does the repository-class difference survive adjustment?

Runs the analysis pre-registered in `PREREGISTRATION_MATCHED_ANALYSIS.md`, and
nothing else. Read that document first; this file is only its executable form.

Committed **before** its first run against `study-artifacts/`. Standard library
only, so anyone can rerun it with a stock interpreter:

    python -m study.matched_analysis                       # real artifacts
    python -m study.matched_analysis --results X --frame Y --descriptions Z --out W

Everything it reports comes from artifacts already published with Study #1: no
network, no re-collection, no re-scoring, no re-classification. The repository
classifier is imported from `composition.py` rather than restated, so it is the
same function that produced the published composition figures.

Primary estimand (contract §3): the change-size-standardized difference in flag
rate, AI-adjacent minus other, in percentage points, computed over the size
strata where both classes are present in sufficient number (common support),
with a 95% cluster bootstrap interval over repositories. Everything else is
labelled secondary and printed after it.

Why common support rather than merging thin strata: merging cascades. A single
thin cell drags its neighbour in, that pair is thin against the next, and five
strata collapse into two — at which point the "adjusted" figure carries exactly
the size imbalance it was meant to remove. Verified on synthetic data with no
class effect by construction: the merging rule reported +5.5 pp, the common
support rule reported ~0. Restricting to common support is a narrower claim,
stated as such, instead of a wider claim that is wrong.
"""
import argparse
import json
import math
import pathlib
import random
import statistics

from .composition import AI_PATTERN, is_ai_adjacent

ART = pathlib.Path("study-artifacts")

# Contract §2: the five published change-size bins, in this order.
BINS = [(0, 20), (21, 100), (101, 500), (501, 2000), (2001, 5000)]
MIN_CELL = 30          # §2: a stratum needs this many in EACH class to count
SEVERITY_FLAG = 3      # a "flag" is severity >= 3, as in the published report
SEED = 2026            # §3
RESAMPLES = 2000       # §3
REPO_UNIT_MIN_PRS = 10  # §4.4


# ---------------------------------------------------------------- loading

def load(results_path, frame_path, descriptions_path):
    """PR rows joined to their repository's class. Analysed rows only."""
    frame = json.loads(pathlib.Path(frame_path).read_text(encoding="utf-8"))
    desc = json.loads(pathlib.Path(descriptions_path).read_text(encoding="utf-8"))

    klass = {}
    for r in frame["included"]:
        name = r["full_name"]
        klass[name] = ("ai" if is_ai_adjacent(name, desc.get(name, {}))
                       else "other")

    rows, skipped = [], {"not_analysed": 0, "unframed_repo": 0,
                         "no_size": 0, "oversize": 0}
    with open(results_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("disposition") != "analysed":
                skipped["not_analysed"] += 1
                continue
            name = r["full_name"]
            if name not in klass:
                skipped["unframed_repo"] += 1
                continue
            size = r.get("changed_lines")
            if size is None:
                skipped["no_size"] += 1
                continue
            if bin_index(size, BINS) is None:
                skipped["oversize"] += 1
                continue
            rows.append({
                "repo": name,
                "klass": klass[name],
                "group": r.get("group"),
                "size": size,
                "flag": (r.get("severity", 0) or 0) >= SEVERITY_FLAG,
            })
    return rows, skipped, klass


# ---------------------------------------------------------------- strata

def bin_index(size, bins):
    for i, (lo, hi) in enumerate(bins):
        if lo <= size <= hi:
            return i
    return None


def stratify(rows, bins):
    """-> {stratum_index: {"ai": [n, k], "other": [n, k]}}"""
    out = {i: {"ai": [0, 0], "other": [0, 0]} for i in range(len(bins))}
    for r in rows:
        i = bin_index(r["size"], bins)
        if i is None:
            continue
        cell = out[i][r["klass"]]
        cell[0] += 1
        cell[1] += int(r["flag"])
    return out


def common_support(strata):
    """§2: strata carrying at least MIN_CELL pull requests in BOTH classes.

    Fixed once on the full sample and then held constant — including inside the
    bootstrap — so that every replicate estimates the same quantity.
    """
    keep, dropped = [], []
    for i, s in sorted(strata.items()):
        if s["ai"][0] >= MIN_CELL and s["other"][0] >= MIN_CELL:
            keep.append(i)
        else:
            dropped.append({"stratum": i, "ai_n": s["ai"][0],
                            "other_n": s["other"][0]})
    return keep, dropped


def merge_thin(rows, bins):
    """Secondary only (§4.6). The cascading merge rule, kept as a contrast."""
    bins = list(bins)
    merged = []
    while len(bins) > 1:
        st = stratify(rows, bins)
        thin = [i for i in st
                if st[i]["ai"][0] < MIN_CELL or st[i]["other"][0] < MIN_CELL]
        if not thin:
            break
        i = max(thin)
        j = i - 1 if i > 0 else 1
        lo, hi = min(bins[i][0], bins[j][0]), max(bins[i][1], bins[j][1])
        merged.append({"merged": [list(bins[i]), list(bins[j])], "into": [lo, hi]})
        bins = [b for k, b in enumerate(bins) if k not in (i, j)]
        bins.insert(min(i, j), (lo, hi))
        bins.sort()
    return bins, merged


# ---------------------------------------------------------------- estimators

def standardized_difference(strata, include):
    """§3 primary: direct standardization to the pooled size distribution of the
    included strata. Returns (rate_ai, rate_other, difference) or Nones."""
    usable = [i for i in include
              if strata[i]["ai"][0] > 0 and strata[i]["other"][0] > 0]
    total = sum(strata[i]["ai"][0] + strata[i]["other"][0] for i in usable)
    if not usable or total == 0:
        return None, None, None
    std = {}
    for c in ("ai", "other"):
        std[c] = sum(
            ((strata[i]["ai"][0] + strata[i]["other"][0]) / total)
            * (strata[i][c][1] / strata[i][c][0])
            for i in usable)
    return std["ai"], std["other"], std["ai"] - std["other"]


def cluster_bootstrap(rows, bins, include, resamples, seed):
    """§3: resample repositories with replacement, all PRs of a drawn repo.
    The stratum set is the one fixed on the full sample."""
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["repo"], []).append(r)
    repos = sorted(by_repo)
    rng = random.Random(seed)
    diffs = []
    for _ in range(resamples):
        draw = []
        for _ in range(len(repos)):
            draw.extend(by_repo[repos[rng.randrange(len(repos))]])
        _, _, d = standardized_difference(stratify(draw, bins), include)
        if d is not None:
            diffs.append(d)
    diffs.sort()
    if len(diffs) < resamples * 0.9:
        return None, None, len(diffs)
    lo = diffs[int(0.025 * (len(diffs) - 1))]
    hi = diffs[int(0.975 * (len(diffs) - 1))]
    return lo, hi, len(diffs)


def cmh(strata, include=None):
    """§4.1 secondary: Mantel-Haenszel common odds ratio with a Robins-Breslow-
    Greenland interval. Runs over ALL strata by default — MH is built for sparse
    strata, so it is the natural check on the common-support restriction."""
    keys = sorted(strata) if include is None else include
    R = S = sP = sPQ_R = sQ = 0.0
    for i in keys:
        s = strata[i]
        n1, k1 = s["ai"]
        n0, k0 = s["other"]
        n = n1 + n0
        if n == 0 or n1 == 0 or n0 == 0:
            continue
        a, b, c, d = k1, n1 - k1, k0, n0 - k0
        r_i, s_i = a * d / n, b * c / n
        R += r_i
        S += s_i
        P, Q = (a + d) / n, (b + c) / n
        sP += P * r_i
        sPQ_R += P * s_i + Q * r_i
        sQ += Q * s_i
    if R == 0 or S == 0:
        return None, None, None
    or_mh = R / S
    se = math.sqrt(sP / (2 * R * R) + sPQ_R / (2 * R * S) + sQ / (2 * S * S))
    return or_mh, or_mh * math.exp(-1.96 * se), or_mh * math.exp(1.96 * se)


def rank_sum(xs, ys):
    """§4.4 secondary: Mann-Whitney U / Wilcoxon rank-sum, normal approximation
    with tie correction. Two-sided p."""
    n1, n2 = len(xs), len(ys)
    if n1 == 0 or n2 == 0:
        return None, None
    pooled = sorted([(v, 0) for v in xs] + [(v, 1) for v in ys])
    ranks, i, ties = [0.0] * len(pooled), 0, 0.0
    while i < len(pooled):
        j = i
        while j + 1 < len(pooled) and pooled[j + 1][0] == pooled[i][0]:
            j += 1
        avg, t = (i + j) / 2.0 + 1, j - i + 1
        ties += t ** 3 - t
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    r1 = sum(rk for rk, (_, g) in zip(ranks, pooled) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2.0
    n = n1 + n2
    sd = math.sqrt((n1 * n2 / 12.0) * ((n + 1) - ties / (n * (n - 1))))
    if sd == 0:
        return u1, None
    z = (u1 - n1 * n2 / 2.0) / sd
    return u1, 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def crude(rows):
    out = {}
    for c in ("ai", "other"):
        sub = [r for r in rows if r["klass"] == c]
        k = sum(1 for r in sub if r["flag"])
        out[c] = {"n": len(sub), "k": k, "rate": (k / len(sub)) if sub else None}
    return out


# ---------------------------------------------------------------- report

def analyse(rows, resamples, seed):
    res = {"contract": "PREREGISTRATION_MATCHED_ANALYSIS.md",
           "classifier_pattern": AI_PATTERN,
           "flag_rule": f"severity >= {SEVERITY_FLAG}",
           "min_cell": MIN_CELL, "seed": seed, "resamples": resamples,
           "n_analysed": len(rows),
           "n_repositories": len({r["repo"] for r in rows}),
           "crude": crude(rows)}

    strata = stratify(rows, BINS)
    include, dropped = common_support(strata)
    covered = sum(strata[i]["ai"][0] + strata[i]["other"][0] for i in include)
    res["bins"] = [list(b) for b in BINS]
    res["strata"] = {str(list(BINS[i])): s for i, s in strata.items()}
    res["common_support"] = {
        "included_bins": [list(BINS[i]) for i in include],
        "excluded_bins": [{"bin": list(BINS[d["stratum"]]), **d} for d in dropped],
        "coverage_prs": covered,
        "coverage_share": covered / len(rows) if rows else None}

    ai_std, other_std, diff = standardized_difference(strata, include)
    lo, hi, ok = cluster_bootstrap(rows, BINS, include, resamples, seed)
    res["primary"] = {
        "estimand": ("size-standardized rate difference over common-support "
                     "strata, ai-adjacent minus other"),
        "standardized_rate_ai": ai_std,
        "standardized_rate_other": other_std,
        "difference_pp": None if diff is None else diff * 100,
        "ci95_pp": None if lo is None else [lo * 100, hi * 100],
        "bootstrap_replicates_used": ok}

    sec = {}
    or_mh, or_lo, or_hi = cmh(strata)
    sec["cmh_odds_ratio_all_strata"] = {"or": or_mh, "ci95": [or_lo, or_hi]}

    by_lang = {}
    for g in sorted({r["group"] for r in rows if r["group"]}):
        sub = [r for r in rows if r["group"] == g]
        st_g = stratify(sub, BINS)
        inc_g, _ = common_support(st_g)
        _, _, d_g = standardized_difference(st_g, inc_g)
        by_lang[g] = {"n": len(sub), "crude": crude(sub),
                      "included_bins": [list(BINS[i]) for i in inc_g],
                      "difference_pp": None if d_g is None else d_g * 100}
    sec["by_language"] = by_lang

    drawn = {}
    for r in rows:
        drawn[r["repo"]] = drawn.get(r["repo"], 0) + 1
    top3 = [k for k, _ in sorted(drawn.items(), key=lambda kv: -kv[1])[:3]]
    kept = [r for r in rows if r["repo"] not in top3]
    st_k = stratify(kept, BINS)
    inc_k, _ = common_support(st_k)
    _, _, d_k = standardized_difference(st_k, inc_k)
    sec["excluding_top3_repositories"] = {
        "excluded": top3, "n": len(kept),
        "included_bins": [list(BINS[i]) for i in inc_k],
        "difference_pp": None if d_k is None else d_k * 100}

    props = {"ai": [], "other": []}
    per_repo = {}
    for r in rows:
        per_repo.setdefault(r["repo"], []).append(r)
    for repo, sub in per_repo.items():
        if len(sub) < REPO_UNIT_MIN_PRS:
            continue
        props[sub[0]["klass"]].append(sum(1 for r in sub if r["flag"]) / len(sub))
    u, p = rank_sum(props["ai"], props["other"])
    sec["repository_as_unit"] = {
        "min_prs": REPO_UNIT_MIN_PRS,
        "n_repositories": {k: len(v) for k, v in props.items()},
        "median_proportion": {k: (statistics.median(v) if v else None)
                              for k, v in props.items()},
        "mann_whitney_u": u, "p_two_sided": p}

    # §4.6 contrast: the cascading-merge rule this analysis deliberately rejects.
    m_bins, merges = merge_thin(rows, BINS)
    st_m = stratify(rows, m_bins)
    _, _, d_m = standardized_difference(st_m, list(range(len(m_bins))))
    sec["merged_strata_contrast"] = {
        "bins": [list(b) for b in m_bins], "merges": merges,
        "difference_pp": None if d_m is None else d_m * 100,
        "note": ("reported to show what the rejected rule would have produced; "
                 "wide strata leave residual size imbalance inside them")}

    size_dist = {}
    for c in ("ai", "other"):
        sub = [r["size"] for r in rows if r["klass"] == c]
        size_dist[c] = {"n": len(sub),
                        "median": statistics.median(sub) if sub else None,
                        "by_bin": {str(list(b)): sum(1 for s in sub
                                                     if b[0] <= s <= b[1])
                                   for b in BINS}}
    sec["size_distribution"] = size_dist  # the mechanism being adjusted for

    res["secondary"] = sec
    return res


def render(res):
    p, c, cs = res["primary"], res["crude"], res["common_support"]
    out = ["# Study #1, Analysis 2 - size-adjusted repository-class difference", "",
           f"Contract: `{res['contract']}` | flag rule: `{res['flag_rule']}` | "
           f"seed {res['seed']} | {res['resamples']} resamples",
           f"{res['n_analysed']} analysed pull requests in "
           f"{res['n_repositories']} repositories.", "",
           "## Crude (unadjusted)", "",
           "| class | n | flagged | rate |", "|---|---|---|---|"]
    for k, label in (("ai", "AI-adjacent"), ("other", "other")):
        r = c[k]
        rate = "n/a" if r["rate"] is None else f"{r['rate']*100:.1f}%"
        out.append(f"| {label} | {r['n']} | {r['k']} | {rate} |")

    diff, ci = p["difference_pp"], p["ci95_pp"]
    share = cs["coverage_share"]
    out += ["", "## Primary - size-standardized difference (common support)", "",
            f"**{'n/a' if diff is None else f'{diff:+.2f} pp'}**, "
            "95% cluster bootstrap CI "
            + ("n/a" if ci is None else f"[{ci[0]:+.2f}, {ci[1]:+.2f}] pp"), "",
            f"Strata used: {cs['included_bins']} - "
            f"{cs['coverage_prs']} pull requests"
            + (f" ({share*100:.1f}% of analysed)" if share else ""),
            f"Strata excluded for thin cells: "
            f"{[e['bin'] for e in cs['excluded_bins']] or 'none'}", "",
            "The estimate holds only where both classes are present in number; "
            "outside that region the data cannot say, and this analysis does "
            "not extrapolate.", "",
            "Read the contract's §6 before quoting this number: the exposure is "
            "a property of the repository, not of the pull request's author, "
            "and the outcome is a structural property of a diff at 6.9% "
            "precision - not a defect rate."]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Study #1, Analysis 2")
    ap.add_argument("--results", default=str(ART / "results.jsonl"))
    ap.add_argument("--frame", default=str(ART / "frame.json"))
    ap.add_argument("--descriptions", default=str(ART / "frame_descriptions.json"))
    ap.add_argument("--out", default=str(ART / "matched_analysis.json"))
    ap.add_argument("--resamples", type=int, default=RESAMPLES)
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()

    rows, skipped, _ = load(a.results, a.frame, a.descriptions)
    res = analyse(rows, a.resamples, a.seed)
    res["skipped_rows"] = skipped
    pathlib.Path(a.out).write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(render(res))
    print(f"\nfull output -> {a.out}")


if __name__ == "__main__":
    main()
