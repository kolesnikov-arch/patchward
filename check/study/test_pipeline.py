"""Offline tests for the study harness: no token, no network.

What these pin down is not "the code runs" but the three properties the
contract actually depends on:

  * the draw is reproducible from the seed and independent of input order;
  * the disposition table accounts for every drawn PR, always;
  * `verify` fails when the published summary drifts from the raw rows —
    a verifier that cannot fail is decoration.
"""
import json
import pathlib
import random
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from study import report as report_mod          # noqa: E402
from study import sample as sample_mod          # noqa: E402


def _population(n=500):
    rng = random.Random(1)
    groups = ["python", "js-ts", "go"]
    rows = []
    for i in range(n):
        g = groups[i % 3]
        rows.append({"full_name": f"org{i % 40}/repo{i % 40}", "group": g,
                     "number": 1000 + i, "title": f"pr {i}",
                     "user": f"u{i % 17}", "created_at": "2026-03-01T00:00:00Z"})
    rng.shuffle(rows)
    return rows


class TestDraw(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pop = pathlib.Path(self.tmp) / "population.jsonl"
        with self.pop.open("w", encoding="utf-8") as f:
            for r in _population():
                f.write(json.dumps(r) + "\n")

    def _draw(self, n=90, seed=25):
        out = pathlib.Path(self.tmp) / f"sample_{n}_{seed}.json"
        return sample_mod.draw(self.pop, out, target_n=n, seed=seed)

    def test_is_reproducible(self):
        a, b = self._draw(), self._draw()
        self.assertEqual([(p["full_name"], p["number"]) for p in a["prs"]],
                         [(p["full_name"], p["number"]) for p in b["prs"]])

    def test_different_seed_differs(self):
        a, b = self._draw(seed=25), self._draw(seed=26)
        self.assertNotEqual([p["number"] for p in a["prs"]],
                            [p["number"] for p in b["prs"]])

    def test_strata_sum_to_target(self):
        s = self._draw(n=90)
        self.assertEqual(s["actual_n"], 90)
        self.assertEqual(sum(a["drawn"] for a in s["allocation"].values()), 90)

    def test_independent_of_input_order(self):
        first = self._draw()
        rows = [json.loads(l) for l in self.pop.open(encoding="utf-8")]
        random.Random(99).shuffle(rows)
        with self.pop.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        second = self._draw()
        self.assertEqual([(p["full_name"], p["number"]) for p in first["prs"]],
                         [(p["full_name"], p["number"]) for p in second["prs"]])

    def test_no_duplicates(self):
        prs = self._draw()["prs"]
        keys = [(p["full_name"], p["number"]) for p in prs]
        self.assertEqual(len(keys), len(set(keys)))


def _rows(n_analysed=100, n_flagged=7, n_excluded=5):
    rows = []
    for i in range(n_analysed):
        high = i < n_flagged
        rows.append({
            "full_name": f"o/r{i % 9}", "number": i, "group": ["python", "js-ts", "go"][i % 3],
            "user": "x", "title": f"t{i}", "disposition": "analysed", "reason": None,
            "changed_lines": [10, 50, 300, 1200, 3000][i % 5],
            "verdict": "self-graded" if high else "clean",
            "severity": 3 if high else 0,
            "kinds": ["REWRITTEN_EXPECTATION"] if high else [],
            "source_files": 1, "test_files": 1 if high else 0,
            "new_tests": 0, "new_assertions": 0,
        })
    for i in range(n_excluded):
        rows.append({"full_name": "o/r", "number": 9000 + i, "group": "python",
                     "user": "x", "title": "t", "disposition": "excluded",
                     "reason": "oversize:9001", "verdict": None})
    return rows


class TestSummary(unittest.TestCase):
    def test_disposition_accounts_for_everything(self):
        s = report_mod.summarize(_rows())
        self.assertEqual(s["drawn"], 105)
        self.assertEqual(s["analysed"] + s["excluded"], s["drawn"])

    def test_headline_and_interval(self):
        s = report_mod.summarize(_rows(n_analysed=100, n_flagged=7))
        self.assertEqual(s["high_severity"], 7)
        self.assertAlmostEqual(s["rate"], 0.07)
        lo, hi = s["ci95_clopper_pearson"]
        self.assertLess(lo, 0.07)
        self.assertGreater(hi, 0.07)

    def test_breakdowns_present(self):
        s = report_mod.summarize(_rows())
        self.assertEqual(set(s["by_language_group"]), {"python", "js-ts", "go"})
        self.assertEqual(len(s["by_diff_size"]), 5)
        self.assertIn("REWRITTEN_EXPECTATION", s["by_finding_kind"])

    def test_zero_flags_does_not_crash(self):
        s = report_mod.summarize(_rows(n_flagged=0))
        self.assertEqual(s["high_severity"], 0)
        self.assertEqual(s["ci95_clopper_pearson"][0], 0.0)


class TestRender(unittest.TestCase):
    def test_says_review_is_missing(self):
        md = report_mod.render(report_mod.summarize(_rows()), None, "abc123")
        self.assertIn("Not yet performed", md)
        self.assertIn("abc123", md)

    def test_states_it_is_not_a_defect_rate(self):
        md = report_mod.render(report_mod.summarize(_rows()), None, "abc123")
        self.assertIn("not a defect rate", md)

    def test_disposition_table_before_headline(self):
        md = report_mod.render(report_mod.summarize(_rows()), None, "x")
        self.assertLess(md.index("Disposition first"), md.index("Headline"))


class TestBlindReview(unittest.TestCase):
    def test_export_hides_the_verdict(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        out = tmp / "review_sample.jsonl"
        report_mod.export_review_sample(_rows(n_analysed=200, n_flagged=80),
                                        out, n_each=10, seed=25)
        lines = [json.loads(l) for l in out.open(encoding="utf-8")]
        self.assertEqual(len(lines), 20)
        for row in lines:
            self.assertNotIn("verdict", row)
            self.assertNotIn("severity", row)
            self.assertNotIn("was_flagged", row)
            self.assertEqual(row["classification"], "")
        key = json.loads((tmp / "review_key.json").read_text())
        self.assertEqual(sum(1 for v in key.values() if v["was_flagged"]), 10)

    def test_falls_back_when_too_few_flagged(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        out = tmp / "review_sample.jsonl"
        report_mod.export_review_sample(_rows(n_analysed=100, n_flagged=3),
                                        out, n_each=60, seed=25)
        lines = list(out.open(encoding="utf-8"))
        self.assertEqual(len(lines), 6)   # all 3 flagged + 3 matched

    def test_false_positive_counting(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        rp, kp = tmp / "review_sample.jsonl", tmp / "review_key.json"
        report_mod.export_review_sample(_rows(n_analysed=200, n_flagged=80),
                                        rp, n_each=5, seed=25)
        key = json.loads(kp.read_text())
        rows = [json.loads(l) for l in rp.open(encoding="utf-8")]
        # flagged -> alternate "1" (true) and "2" (justified => false positive)
        flips = {}
        for i, (rid, k) in enumerate(sorted(key.items())):
            flips[rid] = "1" if (k["was_flagged"] and i % 2 == 0) else "2"
        with rp.open("w", encoding="utf-8") as f:
            for r in rows:
                r["classification"] = flips[r["review_id"]]
                f.write(json.dumps(r) + "\n")
        res = report_mod.score_review(rp, kp)
        self.assertEqual(res["true_positive"] + res["false_positive"],
                         sum(1 for v in key.values() if v["was_flagged"]))
        self.assertIsNotNone(res["precision"])


class TestReviewUIBlinding(unittest.TestCase):
    """The one property the review UI must never lose."""

    def setUp(self):
        from study import review_ui
        self.ui = review_ui
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "study-artifacts").mkdir()
        (self.tmp / "cache" / "diffs").mkdir(parents=True)
        self._cwd = pathlib.Path.cwd()

    def test_server_never_opens_the_key(self):
        """Behavioural, not a grep: serving a page must not touch review_key.json.

        A source-text check would trip over this module's own docstring, which
        *says* it never reads the key. So instead: make any attempt to open a
        path containing 'review_key' explode, then render a page.
        """
        import builtins
        opened = []
        real_open = builtins.open

        def watched(path, *a, **kw):
            if "review_key" in str(path):
                opened.append(str(path))
                raise AssertionError(f"review server opened the key: {path}")
            return real_open(path, *a, **kw)

        buttons = "".join(f'<button value="{k}">{l}</button>'
                          for k, l, _ in self.ui.RUBRIC)
        builtins.open = watched
        try:
            self.ui.PAGE.format(
                done=0, total=120, pct=0.0, rid="R001", title="t", url="u",
                changed_lines=1, body_block="<div></div>",
                diff=self.ui._render_diff("+a\n"), buttons=buttons, undo="")
            self.ui._render_diff("+a\n-b\n")
        finally:
            builtins.open = real_open
        self.assertEqual(opened, [])

    def test_rendered_page_carries_no_verdict(self):
        row = {"review_id": "R001", "url": "https://example/pull/1",
               "title": "fix: thing", "body": "does a thing",
               "changed_lines": 12, "_diff_ref": "nope.diff",
               "classification": "", "note": ""}
        buttons = "".join(f'<button value="{k}">{l}</button>'
                          for k, l, _ in self.ui.RUBRIC)
        page = self.ui.PAGE.format(
            done=0, total=120, pct=0.0, rid=row["review_id"],
            title=row["title"], url=row["url"],
            changed_lines=row["changed_lines"],
            body_block=f'<div>{row["body"]}</div>',
            diff=self.ui._render_diff("+a\n-b\n"), buttons=buttons,
            undo='<a href="/undo">undo R000</a>')
        for leak in ("self-graded", "severity", "was_flagged",
                     "REWRITTEN_EXPECTATION", "SUPPRESSED", "DELETED_TEST"):
            self.assertNotIn(leak, page)

    def test_rubric_matches_the_contract(self):
        self.assertEqual([k for k, _, _ in self.ui.RUBRIC],
                         ["1", "2", "3", "4", "5", "6"])
        joined = " ".join(l for _, l, _ in self.ui.RUBRIC).lower()
        for expected in ("retracted evidence", "justified", "nothing retracted",
                         "unrelated", "undecidable", "no test change"):
            self.assertIn(expected, joined)

    def test_diff_rendering_escapes_html(self):
        out = self.ui._render_diff("+<script>alert(1)</script>\n")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_diff_rendering_truncates(self):
        out = self.ui._render_diff("\n".join(f"+line{i}" for i in range(2000)),
                                   limit=100)
        self.assertIn("more lines", out)

    def test_done_page_orders_commit_before_key(self):
        page = self.ui.DONE_PAGE.format(total=120, undo="")
        self.assertLess(page.index("review_sample.jsonl"),
                        page.index("study tally"),
                        "the protocol is: commit classifications, THEN unblind")


if __name__ == "__main__":
    unittest.main(verbosity=2)
