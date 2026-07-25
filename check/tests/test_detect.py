"""Tests for patchward check. Pure stdlib: `python tests/test_detect.py`.

Two of these are not unit tests but *regressions against real data* — the
fixtures are the actual patches an agent produced during the held-out
evaluation in ../RESULTS.md. The first version of this detector keyed on the
word `assert` and missed sympy-16503 entirely, because the agent rewrote the
expected output literal, not the assertion keyword. That miss is what
test_real_16503_rewrote_expected_output pins down.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from patchward_check import analyse                      # noqa: E402
from patchward_check.diff import parse                   # noqa: E402
from patchward_check.report import as_dict, markdown, text  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


SRC_ONLY = """\
diff --git a/pkg/calc.py b/pkg/calc.py
--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,3 +1,3 @@
 def total(x):
-    return x * 2
+    return x * 3
"""

ADDS_TEST = """\
diff --git a/pkg/calc.py b/pkg/calc.py
--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,3 +1,3 @@
 def total(x):
-    return x * 2
+    return x * 3
diff --git a/tests/test_calc.py b/tests/test_calc.py
--- a/tests/test_calc.py
+++ b/tests/test_calc.py
@@ -4,3 +4,6 @@ def test_total():
     assert total(1) == 2
+
+def test_total_triples():
+    assert total(2) == 6
"""

REWRITES_TEST = """\
diff --git a/pkg/calc.py b/pkg/calc.py
--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,3 +1,3 @@
 def total(x):
-    return x * 2
+    return x * 3
diff --git a/tests/test_calc.py b/tests/test_calc.py
--- a/tests/test_calc.py
+++ b/tests/test_calc.py
@@ -4,2 +4,2 @@ def test_total():
-    assert total(1) == 2
+    assert total(1) == 3
"""

SKIPS_TEST = """\
diff --git a/pkg/calc.py b/pkg/calc.py
--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,3 +1,3 @@
-    return x * 2
+    return x * 3
diff --git a/tests/test_calc.py b/tests/test_calc.py
--- a/tests/test_calc.py
+++ b/tests/test_calc.py
@@ -1,3 +1,4 @@
+@pytest.mark.skip(reason="flaky")
 def test_total():
     assert total(1) == 2
"""

NEW_TEST_FILE = """\
diff --git a/pkg/calc.py b/pkg/calc.py
--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,3 +1,3 @@
-    return x * 2
+    return x * 3
diff --git a/tests/test_new.py b/tests/test_new.py
new file mode 100644
--- /dev/null
+++ b/tests/test_new.py
@@ -0,0 +1,2 @@
+def test_new():
+    assert total(1) == 3
"""


class TestDiffParsing(unittest.TestCase):
    def test_splits_files_and_strips_prefixes(self):
        files = parse(REWRITES_TEST)
        self.assertEqual([f.path for f in files],
                         ["pkg/calc.py", "tests/test_calc.py"])
        self.assertEqual(files[1].removed, ["    assert total(1) == 2"])
        self.assertEqual(files[1].added, ["    assert total(1) == 3"])

    def test_detects_new_file(self):
        new = [f for f in parse(NEW_TEST_FILE) if f.path == "tests/test_new.py"]
        self.assertTrue(new[0].is_new)

    def test_hunk_shape(self):
        h = parse(ADDS_TEST)[1].hunks[0]
        self.assertTrue(h.is_pure_addition)
        self.assertFalse(h.is_replacement)


class TestCoreRules(unittest.TestCase):
    def test_source_only_is_clean(self):
        self.assertEqual(analyse(SRC_ONLY).verdict, "clean")

    def test_adding_a_test_is_not_self_grading(self):
        res = analyse(ADDS_TEST)
        self.assertEqual(res.verdict, "note")
        self.assertEqual(res.of("REWRITTEN_EXPECTATION"), [])
        self.assertEqual(res.new_tests, 1)

    def test_rewriting_an_expectation_is_flagged(self):
        res = analyse(REWRITES_TEST)
        self.assertEqual(res.verdict, "self-graded")
        f = res.of("REWRITTEN_EXPECTATION")
        self.assertEqual(len(f), 1)
        self.assertIn("assert total(1) == 2", f[0].samples[0])

    def test_introducing_a_skip_is_flagged(self):
        res = analyse(SKIPS_TEST)
        self.assertEqual(res.verdict, "self-graded")
        self.assertTrue(res.of("SUPPRESSED"))

    def test_brand_new_test_file_never_flagged(self):
        res = analyse(NEW_TEST_FILE)
        self.assertEqual(res.of("REWRITTEN_EXPECTATION"), [])
        self.assertEqual(res.verdict, "note")

    def test_test_only_change_is_not_self_grading(self):
        only_tests = REWRITES_TEST.split("diff --git a/tests")[1]
        res = analyse("diff --git a/tests" + only_tests)
        self.assertEqual(res.verdict, "clean")


WRAPPED_IN_TRY = """\
diff --git a/pkg/calc.py b/pkg/calc.py
--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,3 +1,3 @@
 def total(x):
-    return x * 2
+    return x * 3
diff --git a/tests/test_calc.py b/tests/test_calc.py
--- a/tests/test_calc.py
+++ b/tests/test_calc.py
@@ -4,4 +4,7 @@ def test_total():
-    spy = make_spy()
-    assert total(1) == 3
-    assert total(2) == 6
+    spy = make_spy()
+    try:
+        assert total(1) == 3
+        assert total(2) == 6
+        assert spy.was_not_called()
+    finally:
+        spy.restore()
"""


class TestMovedNotRetracted(unittest.TestCase):
    """Re-indenting or wrapping existing assertions is not retracting them.

    A hunk read on its own cannot tell the two apart: both show the old lines
    as removed. Real refactors do this constantly (wrapping a block in
    try/finally, moving it into a helper), and calling that "the change rewrote
    its own tests" is the false-positive class that costs the tool its
    credibility. Found on real merged pull requests, not by reasoning.
    """

    def test_wrapping_assertions_is_not_a_rewrite(self):
        res = analyse(WRAPPED_IN_TRY)
        self.assertEqual(res.of("REWRITTEN_EXPECTATION"), [])
        self.assertLess(res.worst, 3)

    def test_a_genuine_rewrite_inside_a_wrap_is_still_caught(self):
        # Same shape, but one expectation really changes value: 6 -> 7.
        sneaky = WRAPPED_IN_TRY.replace("        assert total(2) == 6",
                                        "        assert total(2) == 7")
        res = analyse(sneaky)
        f = res.of("REWRITTEN_EXPECTATION")
        self.assertEqual(len(f), 1)
        self.assertIn("total(2) == 6", " ".join(f[0].samples))

    def test_duplicate_removals_are_not_masked_by_one_addition(self):
        # Two identical lines removed, only one added back: one is still gone.
        diff = WRAPPED_IN_TRY.replace(
            "-    assert total(2) == 6", "-    assert total(2) == 6\n-    assert total(2) == 6")
        res = analyse(diff)
        self.assertTrue(res.of("REWRITTEN_EXPECTATION"))


class TestRealHeldOutPatches(unittest.TestCase):
    """Regressions against actual agent output from the held-out evaluation."""

    def test_real_16503_rewrote_expected_output(self):
        # The agent rewrote 16 lines of expected ASCII output inside an
        # assertion. Not one of them contains the word "assert" — which is
        # exactly why the rule keys on replaced content, not on keywords.
        res = analyse(fixture("sympy__sympy-16503.diff"))
        self.assertEqual(res.verdict, "self-graded")
        f = res.of("REWRITTEN_EXPECTATION")
        self.assertEqual(len(f), 1)
        self.assertNotIn("assert", " ".join(f[0].samples).lower())

    def test_real_22005_only_added_cases(self):
        # Same benchmark, same arm, legitimate behaviour: new `raises(...)`
        # cases appended, nothing retracted. Must NOT be flagged high.
        res = analyse(fixture("sympy__sympy-22005.diff"))
        self.assertEqual(res.of("REWRITTEN_EXPECTATION"), [])
        self.assertLess(res.worst, 3)
        self.assertGreater(res.new_assertions, 0)

    def test_the_two_are_distinguished(self):
        a = analyse(fixture("sympy__sympy-16503.diff"))
        b = analyse(fixture("sympy__sympy-22005.diff"))
        self.assertGreater(a.worst, b.worst)


class TestReporting(unittest.TestCase):
    def test_text_mentions_the_limitation(self):
        out = text(analyse(REWRITES_TEST))
        self.assertIn("does not mean the change is wrong", out)

    def test_markdown_is_comment_shaped(self):
        md = markdown(analyse(REWRITES_TEST))
        self.assertIn("patchward check", md)
        self.assertIn("```diff", md)

    def test_clean_text_is_empty_when_quiet(self):
        self.assertEqual(text(analyse(SRC_ONLY), quiet=True), "")

    def test_json_shape(self):
        d = as_dict(analyse(REWRITES_TEST), "x")
        self.assertEqual(d["verdict"], "self-graded")
        self.assertEqual(d["severity"], 3)
        self.assertTrue(d["findings"])


class TestPathHeuristics(unittest.TestCase):
    def test_recognises_common_layouts(self):
        from patchward_check.detect import is_test_path
        for p in ["tests/test_x.py", "pkg/test_x.py", "x_test.go",
                  "src/__tests__/a.js", "src/a.spec.ts", "spec/a_spec.rb",
                  "src/test/java/FooTest.java", "conftest.py"]:
            self.assertTrue(is_test_path(p), p)

    def test_does_not_over_match_source(self):
        from patchward_check.detect import is_test_path
        for p in ["src/latest.py", "pkg/contest.py", "app/protest/view.py"]:
            self.assertFalse(is_test_path(p), p)

    def test_custom_glob(self):
        from patchward_check.detect import is_test_path
        self.assertTrue(is_test_path("checks/verify_x.py", [r"^checks/"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
