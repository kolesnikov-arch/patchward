"""The strata rule is the whole analysis, so it gets a test that can fail.

Ground truth in the fixture: flag probability is a function of **change size
alone**. There is no repository-class effect. AI-adjacent repositories are given
larger changes, so an unadjusted comparison must show a gap, and a correctly
adjusted one must not.

This is the test that changed the pre-registered rule
(`../PREREGISTRATION_MATCHED_ANALYSIS.md` §2) before it was committed: the
cascading-merge rule reports a difference whose interval excludes zero on data
with no effect in it, because merging leaves the size imbalance inside the wide
strata it creates. Run it before trusting any number this module prints:

    python study/test_matched_analysis.py
"""
import pathlib
import random
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))        # `check/`, so `study` is a package

from study.matched_analysis import (BINS, cluster_bootstrap,  # noqa: E402
                                    common_support, crude, merge_thin,
                                    standardized_difference, stratify)

# Flag probability by size band — the only thing that drives the outcome.
P_BY_BAND = [(20, 0.04), (100, 0.20), (500, 0.35), (2000, 0.54), (5000, 0.59)]


def p_for(size):
    for hi, p in P_BY_BAND:
        if size <= hi:
            return p
    return P_BY_BAND[-1][1]


def synthetic(seed=7, repos=150, prs_per_repo=20):
    """150 repositories, every third one AI-adjacent and shifted to larger diffs."""
    rng = random.Random(seed)
    rows = []
    for i in range(repos):
        ai = i % 3 == 0
        name = f"org{i}/repo{i}"
        group = ["python", "js-ts", "go"][i % 3]
        for _ in range(prs_per_repo):
            size = min(int(abs(rng.gauss(400 if ai else 90,
                                         250 if ai else 60))) + 1, 5000)
            rows.append({"repo": name, "klass": "ai" if ai else "other",
                         "group": group, "size": size,
                         "flag": rng.random() < p_for(size)})
    return rows


class TestStrataRule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = synthetic()
        cls.strata = stratify(cls.rows, BINS)
        cls.include, cls.dropped = common_support(cls.strata)

    def test_fixture_has_a_crude_gap_to_explain(self):
        """If the fixture stopped being confounded, the test proves nothing."""
        c = crude(self.rows)
        self.assertGreater(c["ai"]["rate"] - c["other"]["rate"], 0.10)

    def test_common_support_drops_the_one_sided_bins(self):
        self.assertTrue(self.include, "no stratum survived — fixture is broken")
        for i in self.include:
            self.assertGreaterEqual(self.strata[i]["ai"][0], 30)
            self.assertGreaterEqual(self.strata[i]["other"][0], 30)
        self.assertTrue(self.dropped, "fixture should have one-sided tails")

    def test_primary_interval_covers_zero_when_there_is_no_effect(self):
        _, _, diff = standardized_difference(self.strata, self.include)
        lo, hi = cluster_bootstrap(self.rows, BINS, self.include, 300, 2026)[:2]
        self.assertIsNotNone(diff)
        self.assertLess(lo, 0.0, f"lower bound {lo:+.4f} excludes zero")
        self.assertGreater(hi, 0.0, f"upper bound {hi:+.4f} excludes zero")

    def test_merging_rule_would_have_invented_an_effect(self):
        """The rejected rule, kept as a regression guard on the reasoning."""
        _, _, adjusted = standardized_difference(self.strata, self.include)
        m_bins, merges = merge_thin(self.rows, BINS)
        _, _, merged = standardized_difference(stratify(self.rows, m_bins),
                                               list(range(len(m_bins))))
        self.assertTrue(merges, "merge rule did not fire — fixture changed")
        self.assertLess(len(m_bins), 3, "merge rule should collapse to coarse strata")
        self.assertGreater(merged - adjusted, 0.02,
                           "merging no longer inflates the estimate; if this is "
                           "genuinely so, revisit the contract's §2 rationale")


if __name__ == "__main__":
    unittest.main(verbosity=2)
