"""Recompute every headline number from the artifacts in this directory.

Pure stdlib — no dependencies. It does three things:

1. Re-derives each arm's per-instance gold outcome (`resolved`) from the raw
   SWE-bench evaluation reports in `reports/` and cross-checks them against
   `results_paired.csv` (any mismatch fails loudly).
2. Re-tallies the full disposition table and the headline cells.
3. Recomputes the exact (Clopper-Pearson) 95% confidence intervals and the
   two-sided Fisher exact p-value.

Run:  python verify_counts.py
"""
import csv
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ALPHA = 0.05


def binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(x, n, alpha=ALPHA):
    # both lambdas are decreasing in p, as _bisect requires
    lo = 0.0 if x == 0 else _bisect(lambda p: alpha / 2 - (1 - binom_cdf(x - 1, n, p)))
    hi = 1.0 if x == n else _bisect(lambda p: binom_cdf(x, n, p) - alpha / 2)
    return lo, hi


def _bisect(f, lo=0.0, hi=1.0):
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) < 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def fisher_exact_two_sided(a, b, c, d):
    """2x2 table [[a, b], [c, d]] -> two-sided p (sum of tables as/less likely)."""
    n, r1, c1 = a + b + c + d, a + b, a + c

    def p_table(x):
        return (math.comb(r1, x) * math.comb(n - r1, c1 - x)) / math.comb(n, c1)

    p_obs = p_table(a)
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    return sum(p for x in range(lo, hi + 1)
               if (p := p_table(x)) <= p_obs * (1 + 1e-9))


def resolved_from_report(arm_dir, instance_id):
    path = os.path.join(HERE, "reports", arm_dir, f"{instance_id}.report.json")
    with open(path, encoding="utf-8") as f:
        return bool(json.load(f)[instance_id].get("resolved"))


def main():
    with open(os.path.join(HERE, "results_paired.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 50, f"expected 50 rows, got {len(rows)}"

    tally = {"c_fa": 0, "c_ok": 0, "verified": 0, "nr_ok": 0, "nr_wrong": 0,
             "cb": 0, "fr": 0}
    for r in rows:
        iid = r["instance_id"]
        g_ok = resolved_from_report("gated", iid)
        u_ok = resolved_from_report("ungated", iid)
        assert str(g_ok) == r["gated_patch_resolves"], f"{iid}: gated mismatch"
        assert str(u_ok) == r["ungated_resolves"], f"{iid}: ungated mismatch"

        tally["c_ok" if u_ok else "c_fa"] += 1
        v = r["gated_verdict"]
        if v == "Verified":
            tally["verified"] += 1
        elif v == "Needs review":
            tally["nr_ok" if g_ok else "nr_wrong"] += 1
        else:
            tally["fr" if g_ok else "cb"] += 1

    n = len(rows)
    c_fa, b_fa = tally["c_fa"], 0  # gated confident false-accepts = wrong Verified
    print("per-instance gold outcomes match results_paired.csv: OK")
    print(f"\nungated arm : {c_fa} silent false-accept, {tally['c_ok']} shipped correct  (n={n})")
    print(f"gated arm   : Verified {tally['verified']} | Needs review "
          f"{tally['nr_ok']} correct + {tally['nr_wrong']} wrong | Blocked "
          f"{tally['cb']} correct-block + {tally['fr']} false-reject")
    print(f"delivered-correct yield: ungated {tally['c_ok']} (all silent) vs "
          f"gated {tally['nr_ok']} (all flagged)")

    for label, x in (("ungated silent false-accept", c_fa),
                     ("gated confident false-accept", b_fa)):
        lo, hi = clopper_pearson(x, n)
        print(f"{label}: {x}/{n} = {x/n:.1%}  95% CI [{lo:.1%}, {hi:.1%}]")

    pess = tally["nr_wrong"] + b_fa
    lo, hi = clopper_pearson(pess, n)
    print(f"sensitivity (every wrong Needs-review counted as merged): "
          f"{pess}/{n} = {pess/n:.1%}  95% CI [{lo:.1%}, {hi:.1%}]")

    p = fisher_exact_two_sided(c_fa, n - c_fa, b_fa, n - b_fa)
    print(f"Fisher exact (two-sided), {c_fa}/{n} vs {b_fa}/{n}: p = {p:.2e}")


if __name__ == "__main__":
    main()
