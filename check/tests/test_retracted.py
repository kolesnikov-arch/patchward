"""What the extraction must and must not report. `python tests/test_retracted.py`.

The cases that matter came from real data, not from reasoning: an expected
literal rewritten without the word `assert` anywhere near it, a refactor that
removes lines only to add them back, and — in `NoiseFoundOnRealRepositories` —
every false positive this view produced across 950 commits of requests, flask
and fastapi.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from patchward_check.retracted import extract, markdown, text  # noqa: E402


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


class NoiseFoundOnRealRepositories(unittest.TestCase):
    """Every case here was a false positive on requests, flask or fastapi."""

    def test_a_trailing_comment_change_is_not_a_retraction(self):
        d = SRC + diff("tests/test_calc.py",
                       " def test_f():\n"
                       "-    x = f()  # ty: ignore[missing-argument, unknown]\n"
                       "+    x = f()  # ty: ignore[missing-argument]\n")
        self.assertEqual(len(extract(d)), 0)

    def test_a_hash_inside_a_string_is_not_a_comment(self):
        """Dropping a real retraction to tidy output is the one trade not allowed."""
        d = SRC + diff("tests/test_calc.py",
                       " def test_f():\n"
                       "-    assert render() == 'tag #1'\n"
                       "+    assert render() == 'tag #2'\n")
        self.assertEqual(len(extract(d)), 1)

    def test_rewrapping_one_expression_is_not_a_retraction(self):
        d = SRC + diff("tests/test_calc.py",
                       " def test_f():\n"
                       "-    order = [\n"
                       "-        r.name\n"
                       "-        for r in rules()\n"
                       "-    ]\n"
                       "+    order = [r.name for r in rules()]\n")
        self.assertEqual(len(extract(d)), 0)

    def test_imports_and_fixtures_are_not_expectations(self):
        d = SRC + diff("tests/test_calc.py",
                       " def test_f():\n"
                       "-from flask.globals import app_ctx\n"
                       "+from flask.testing import FlaskClient\n"
                       "-@pytest.fixture(scope='session')\n"
                       "+@pytest.fixture\n")
        self.assertEqual(len(extract(d)), 0)

    def test_a_large_rewrite_is_summarised_not_listed(self):
        body = "".join(f"-    assert f({i}) == {i}\n+    assert f({i}) == {i + 1}\n"
                       for i in range(20))
        r = extract(SRC + diff("tests/test_calc.py", " def test_f():\n" + body))
        self.assertEqual([i.kind for i in r.items], ["bulk"])
        self.assertIn("20", r.items[0].was)
        self.assertIn("too large to list line by line", text(r))



class SilenceAndScope(unittest.TestCase):
    """Found by pointing the tool at its own repository and at open-webui."""

    def test_a_docstring_edit_at_the_head_of_a_test_file_is_not_a_retraction(self):
        d = SRC + ("diff --git a/tests/test_x.py b/tests/test_x.py\n"
                   "--- a/tests/test_x.py\n+++ b/tests/test_x.py\n"
                   "@@ -1,4 +1,4 @@\n"
                   '-The cases that matter are the ones found on real data.\n'
                   '+The cases that matter came from real data, not reasoning.\n')
        self.assertEqual(len(extract(d)), 0)

    def test_a_real_expectation_at_the_head_still_counts(self):
        d = SRC + ("diff --git a/tests/test_x.py b/tests/test_x.py\n"
                   "--- a/tests/test_x.py\n+++ b/tests/test_x.py\n"
                   "@@ -1,4 +1,4 @@\n"
                   "-    assert f() == 5\n"
                   "+    assert f() == 7\n")
        self.assertEqual(len(extract(d)), 1)

    def test_a_deep_hunk_is_not_treated_as_the_head(self):
        """The sharpest real case lives hundreds of lines into a file."""
        d = SRC + ("diff --git a/tests/test_pretty.py b/tests/test_pretty.py\n"
                   "--- a/tests/test_pretty.py\n+++ b/tests/test_pretty.py\n"
                   "@@ -618,4 +618,4 @@\n"
                   "-    expected = 'x + 1'\n"
                   "+    expected = '1 + x'\n")
        self.assertEqual(len(extract(d)), 1)

    def test_a_source_only_change_records_the_source_files(self):
        """So the caller can tell 'nothing retracted' from 'nothing checked'."""
        r = extract(SRC)
        self.assertEqual(len(r), 0)
        self.assertEqual(r.source_files, ["app/calc.py"])
        self.assertEqual(r.test_files, [])


class LargeHunks(unittest.TestCase):
    """A vendored or generated diff must not cost minutes."""

    def test_a_hunk_past_the_pairing_limit_is_reported_without_pairing(self):
        from patchward_check.retracted import PAIRING_LIMIT
        body = "".join(f"-    assert f({i}) == {i}\n+    assert f({i}) == {i+1}\n"
                       for i in range(PAIRING_LIMIT + 5))
        r = extract(SRC + diff("tests/test_calc.py", " def test_f():\n" + body))
        self.assertEqual([i.kind for i in r.items], ["bulk"])

    def test_it_finishes_quickly(self):
        import time
        body = "".join(f"-    assert f({i}) == {i}\n+    assert g({i}) == {i*7}\n"
                       for i in range(1500))
        t0 = time.time()
        extract(SRC + diff("tests/test_calc.py", " def test_f():\n" + body))
        self.assertLess(time.time() - t0, 5.0)

if __name__ == "__main__":
    unittest.main()
