"""What the extraction must and must not report.

The cases that matter are the ones found on real data: an expected literal
rewritten without the word `assert` anywhere near it, and a refactor that removes
lines only to add them back.
"""
import unittest

from patchward_check.retracted import extract, markdown, text


def diff(path, hunk, old=None):
    old = old or path
    return (f"diff --git a/{old} b/{path}\n"
            f"--- a/{old}\n+++ b/{path}\n"
            f"@@ -1,5 +1,5 @@\n{hunk}")


SRC = diff("app/calc.py", " def f():\n-    return 5\n+    return 7\n")


class Extraction(unittest.TestCase):

    def test_rewritten_expectation_is_paired_before_and_after(self):
        d = SRC + diff("tests/test_calc.py",
                       " def test_f():\n-    assert f() == 5\n+    assert f() == 7\n")
        r = extract(d)
        self.assertEqual(len(r), 1)
        item = r.items[0]
        self.assertEqual(item.kind, "changed")
        self.assertIn("== 5", item.was)
        self.assertIn("== 7", item.now)

    def test_expected_literal_without_the_word_assert(self):
        """The sharpest real case rewrote the expected value, not the keyword."""
        d = SRC + diff("tests/test_pretty.py",
                       " def test_pretty():\n"
                       "-    expected = 'x + 1'\n"
                       "+    expected = '1 + x'\n")
        r = extract(d)
        self.assertEqual(len(r), 1)
        self.assertEqual(r.items[0].kind, "changed")

    def test_moved_lines_are_not_retractions(self):
        """Re-indenting into a try/finally removes and re-adds the same lines."""
        d = SRC + diff("tests/test_calc.py",
                       " def test_f():\n"
                       "-    assert f() == 5\n"
                       "+    try:\n"
                       "+    assert f() == 5\n"
                       "+    finally:\n"
                       "+        cleanup()\n")
        self.assertEqual(len(extract(d)), 0)

    def test_deleted_test_case_is_reported_without_a_replacement(self):
        d = SRC + diff("tests/test_calc.py",
                       " import pytest\n-def test_edge_case():\n-    assert f(0) == 0\n")
        r = extract(d)
        kinds = {i.kind for i in r.items}
        self.assertEqual(kinds, {"removed"})
        self.assertTrue(all(i.now is None for i in r.items))

    def test_deleted_non_check_lines_are_ignored(self):
        """An import or a fixture is not an expectation."""
        d = SRC + diff("tests/test_calc.py",
                       " import pytest\n-import os\n-BASE_DIR = '/tmp'\n")
        self.assertEqual(len(extract(d)), 0)

    def test_added_suppression_is_a_retraction(self):
        d = SRC + diff("tests/test_calc.py",
                       " def test_f():\n+    @pytest.mark.skip('flaky')\n")
        r = extract(d)
        self.assertEqual([i.kind for i in r.items], ["suppressed"])
        self.assertIsNone(r.items[0].was)

    def test_new_test_file_retracts_nothing(self):
        d = ("diff --git a/tests/test_new.py b/tests/test_new.py\n"
             "--- /dev/null\n+++ b/tests/test_new.py\n"
             "@@ -0,0 +1,2 @@\n+def test_x():\n+    assert True\n")
        self.assertEqual(len(extract(d)), 0)

    def test_source_only_change_retracts_nothing(self):
        self.assertEqual(len(extract(SRC)), 0)

    def test_source_files_are_recorded_separately(self):
        d = SRC + diff("tests/test_calc.py",
                       " def test_f():\n-    assert f() == 5\n+    assert f() == 7\n")
        r = extract(d)
        self.assertEqual(r.source_files, ["app/calc.py"])
        self.assertEqual(r.test_files, ["tests/test_calc.py"])


class Rendering(unittest.TestCase):

    def setUp(self):
        self.r = extract(SRC + diff(
            "tests/test_calc.py",
            " def test_f():\n-    assert f() == 5\n+    assert f() == 7\n"))

    def test_no_verdict_word_appears_anywhere(self):
        for out in (text(self.r), markdown(self.r)):
            low = out.lower()
            for word in ("severity", "high", "warning", "violation", "suspicious",
                         "self-graded", "failed"):
                self.assertNotIn(word, low, f"{word!r} leaked into the output")

    def test_empty_result_renders_empty(self):
        empty = extract(SRC)
        self.assertEqual(text(empty), "")
        self.assertEqual(markdown(empty), "")

    def test_markdown_uses_a_diff_fence_so_github_colours_it(self):
        self.assertIn("```diff", markdown(self.r))

    def test_the_caveat_always_ships_with_the_finding(self):
        for out in (text(self.r), markdown(self.r)):
            self.assertIn("not judged", out)

    def test_pure_removal_is_marked_in_text(self):
        r = extract(SRC + diff("tests/test_calc.py",
                               " import pytest\n-def test_gone():\n-    assert f(0) == 0\n"))
        self.assertIn("(removed)", text(r))


if __name__ == "__main__":
    unittest.main()
