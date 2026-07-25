"""Exact confidence intervals that survive n = 3000. Pure stdlib.

Why this file exists instead of reusing `self-check/fa_patchward/stats.py`:
that implementation sums `math.comb(n, i) * p**i * (1-p)**(n-i)` directly. At
n = 50 it is exact and fine. At n = 3000 it is neither — `math.comb(3000, 1500)`
is an integer around 10^902, `p**i` underflows to 0.0, and their product raises
`OverflowError: int too large to convert to float`. The study needs intervals at
n = 3000, so the same quantity is computed through the regularized incomplete
beta function instead, which is what Clopper-Pearson is defined in terms of
anyway:

    lower = B^-1(alpha/2;   k,   n-k+1)
    upper = B^-1(1-alpha/2; k+1, n-k)

Continued-fraction evaluation (Lentz), all in log space. Verified in
`test_stats.py` against the published held-out figures, which were produced by
the original routine — so the two agree where the original still works.
"""
import math

ALPHA = 0.05
_EPS = 3.0e-12
_FPMIN = 1.0e-300


def _betacf(a, b, x, itmax=300):
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _FPMIN:
        d = _FPMIN
    d = 1.0 / d
    h = d

    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            return h
    return h


def betainc(a, b, x):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log1p(-x))
    front = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _beta_quantile(p, a, b):
    """Invert I_x(a, b) = p by bisection. Monotone in x, so this is safe."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if betainc(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def clopper_pearson(k, n, alpha=ALPHA):
    """Exact two-sided Clopper-Pearson interval for k successes in n trials."""
    if n == 0:
        return 0.0, 1.0
    if k < 0 or k > n:
        raise ValueError(f"k={k} out of range for n={n}")
    lo = 0.0 if k == 0 else _beta_quantile(alpha / 2.0, k, n - k + 1)
    hi = 1.0 if k == n else _beta_quantile(1.0 - alpha / 2.0, k + 1, n - k)
    return lo, hi


def wilson(k, n, z=1.959963984540054):
    """Wilson interval — reported alongside as a sanity check, never as the headline."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)
