"""Exact confidence intervals — pure stdlib, no dependencies.

These are the same routines used by patchward's published `verify_counts.py`,
kept here verbatim so a number this gauge reports is computed the same way as the
reference result you are comparing yourself against.
"""
import math

ALPHA = 0.05


def binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def _bisect(f, lo=0.0, hi=1.0):
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) < 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def clopper_pearson(x, n, alpha=ALPHA):
    """Exact (Clopper-Pearson) two-sided CI for a binomial proportion x/n."""
    if n == 0:
        return 0.0, 1.0
    # both lambdas are decreasing in p, as _bisect requires
    lo = 0.0 if x == 0 else _bisect(lambda p: alpha / 2 - (1 - binom_cdf(x - 1, n, p)))
    hi = 1.0 if x == n else _bisect(lambda p: binom_cdf(x, n, p) - alpha / 2)
    return lo, hi
