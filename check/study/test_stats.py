"""Verify the interval routine against the already-published held-out figures.

The numbers in RESULTS.md were computed by the original `math.comb` routine.
If this implementation disagrees with them, one of the two is wrong and the
study cannot proceed — so this file is a gate, not a formality.
"""
import sys
import unittest

from stats import clopper_pearson, betainc, wilson


class TestAgainstPublishedFigures(unittest.TestCase):
    """RESULTS.md §1: 17/50 -> [21.2%, 48.8%]; 0/50 -> [0.0%, 7.1%]."""

    def test_ungated_arm_17_of_50(self):
        lo, hi = clopper_pearson(17, 50)
        self.assertAlmostEqual(lo * 100, 21.2, places=1)
        self.assertAlmostEqual(hi * 100, 48.8, places=1)

    def test_gated_arm_0_of_50(self):
        lo, hi = clopper_pearson(0, 50)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi * 100, 7.1, places=1)

    def test_sensitivity_row_14_of_50(self):
        # RESULTS.md §2: 14/50 -> [16.2%, 42.5%]
        lo, hi = clopper_pearson(14, 50)
        self.assertAlmostEqual(lo * 100, 16.2, places=1)
        self.assertAlmostEqual(hi * 100, 42.5, places=1)


class TestTextbookValues(unittest.TestCase):
    def test_2_of_10(self):
        lo, hi = clopper_pearson(2, 10)
        self.assertAlmostEqual(lo, 0.02521, places=4)
        self.assertAlmostEqual(hi, 0.55610, places=4)

    def test_full_and_empty(self):
        self.assertEqual(clopper_pearson(0, 20)[0], 0.0)
        self.assertEqual(clopper_pearson(20, 20)[1], 1.0)

    def test_betainc_endpoints(self):
        self.assertEqual(betainc(2, 3, 0.0), 0.0)
        self.assertEqual(betainc(2, 3, 1.0), 1.0)
        self.assertAlmostEqual(betainc(1, 1, 0.37), 0.37, places=9)


class TestSurvivesStudyScale(unittest.TestCase):
    """The reason this module exists: n=3000 must not overflow or hang."""

    def test_n_3000(self):
        for k in (0, 1, 60, 150, 1500, 2999, 3000):
            lo, hi = clopper_pearson(k, 3000)
            self.assertTrue(0.0 <= lo <= k / 3000 <= hi <= 1.0,
                            f"k={k}: [{lo}, {hi}]")

    def test_original_routine_would_have_failed(self):
        """Pin the failure this module was written to avoid."""
        import math

        def binom_cdf_naive(k, n, p):
            return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
                       for i in range(k + 1))

        with self.assertRaises((OverflowError, ValueError)):
            binom_cdf_naive(1500, 3000, 0.5)

    def test_interval_narrows_with_n(self):
        w_small = lambda: clopper_pearson(5, 50)
        w_big = lambda: clopper_pearson(300, 3000)
        s = w_small(); b = w_big()
        self.assertLess(b[1] - b[0], s[1] - s[0])

    def test_wilson_is_close_but_not_identical(self):
        cp = clopper_pearson(150, 3000)
        w = wilson(150, 3000)
        self.assertLess(abs(cp[0] - w[0]), 0.01)
        self.assertLess(abs(cp[1] - w[1]), 0.01)
        self.assertNotEqual(cp, w)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
