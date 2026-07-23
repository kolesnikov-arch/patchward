"""Self-test with synthetic data — no Docker, no network, stdlib only.

Runs the scorer/reporter/verify path end-to-end against handmade predictions and
reports with known outcomes, and checks the disposition counts, the headline
number, the exact CI, and that verify() round-trips. Run:

    python tests/test_gauge.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fa_patchward import report as R
from fa_patchward.model import (ABSTAINED, APPLY_FAILED, SHIPPED_CORRECT,
                                SILENT_FALSE_ACCEPT, UNSCORED, classify)
from fa_patchward.stats import clopper_pearson

# instance_id -> (model_patch, report_or_None, expected_outcome)
CASES = {
    "django__django-1": ("diff --git a/x", {"resolved": True,
                          "patch_successfully_applied": True}, SHIPPED_CORRECT),
    "django__django-2": ("diff --git a/y", {"resolved": False,
                          "patch_successfully_applied": True}, SILENT_FALSE_ACCEPT),
    "sympy__sympy-3": ("diff --git a/z", {"resolved": False,
                        "patch_successfully_applied": True}, SILENT_FALSE_ACCEPT),
    "sympy__sympy-4": ("diff --git a/w", {"resolved": False,
                        "patch_successfully_applied": False}, APPLY_FAILED),
    "sphinx__sphinx-5": ("", None, ABSTAINED),
    "sphinx__sphinx-6": ("diff --git a/q", None, UNSCORED),
}


def test_classify_units():
    for iid, (patch, rep, expected) in CASES.items():
        d = classify(iid, "", patch, rep)
        assert d.outcome == expected, f"{iid}: got {d.outcome}, want {expected}"


def test_ci_matches_reference_style():
    # 17/50 -> published reference CI is [21.2%, 48.8%] (patchward RESULTS.md).
    lo, hi = clopper_pearson(17, 50)
    assert abs(lo - 0.212) < 1e-3 and abs(hi - 0.488) < 1e-3, (lo, hi)
    # degenerate arm: 0 events must not crash and spans from 0.
    lo0, _ = clopper_pearson(0, 50)
    assert lo0 == 0.0


def test_end_to_end(tmp):
    preds = os.path.join(tmp, "predictions.jsonl")
    reports = os.path.join(tmp, "reports")
    os.makedirs(reports)
    with open(preds, "w", encoding="utf-8") as f:
        for iid, (patch, rep, _) in CASES.items():
            f.write(json.dumps({"instance_id": iid, "model_name_or_path": "t",
                                "model_patch": patch}) + "\n")
            if rep is not None:
                with open(os.path.join(reports, f"{iid}.report.json"), "w",
                          encoding="utf-8") as rf:
                    json.dump({iid: rep}, rf)

    out = os.path.join(tmp, "report")
    s = R.report(preds, reports, out, "test-agent", ids=list(CASES))

    assert s["counts"][SHIPPED_CORRECT] == 1
    assert s["counts"][SILENT_FALSE_ACCEPT] == 2
    assert s["counts"][APPLY_FAILED] == 1
    assert s["counts"][ABSTAINED] == 1
    assert s["counts"][UNSCORED] == 1
    assert s["ships"] == 3                      # 1 correct + 2 wrong
    assert abs(s["rate_of_ships"] - 2 / 3) < 1e-9
    exp_lo, exp_hi = clopper_pearson(2, 3)
    assert s["ci95"] == [exp_lo, exp_hi]

    for name in ("results.csv", "summary.json", "RESULTS.md"):
        assert os.path.getsize(os.path.join(out, name)) > 0, name

    # verify() must recompute the same outcomes from the raw reports.
    v = R.verify(out, reports, preds, ids=list(CASES))
    assert v["silent_false_accept"] == 2 and v["ships"] == 3


def test_reconciles_published_number():
    """If the sibling patchward artifacts are present, the gauge must reproduce
    the published ungated number (17 silent false-accepts / 33 correct / 50
    ships) from the REAL SWE-bench harness reports. Skipped on a bare install."""
    here = os.path.dirname(os.path.abspath(__file__))
    art = os.path.abspath(os.path.join(here, "..", "..", "evaluation-artifacts"))
    preds = os.path.join(art, "predictions_ungated.jsonl")
    reports = os.path.join(art, "reports", "ungated")
    if not (os.path.exists(preds) and os.path.isdir(reports)):
        print("skip real-data reconciliation (patchward artifacts not present)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        s = R.report(preds, reports, tmp, "ungated-arm")
    assert s["counts"][SILENT_FALSE_ACCEPT] == 17, s["counts"]
    assert s["counts"][SHIPPED_CORRECT] == 33, s["counts"]
    assert s["counts"][ABSTAINED] == 0, s["counts"]
    assert s["ships"] == 50 and s["silent_false_accept"] == 17
    lo, hi = s["ci95"]
    assert abs(lo - 0.212) < 1e-3 and abs(hi - 0.488) < 1e-3, (lo, hi)
    print("real-data reconciliation OK: reproduces published 17/50 (CI 21.2-48.8%)")


def main():
    test_classify_units()
    test_ci_matches_reference_style()
    with tempfile.TemporaryDirectory() as tmp:
        test_end_to_end(tmp)
    test_reconciles_published_number()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
