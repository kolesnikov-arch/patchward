"""Task/prediction/disposition model and the honesty rules for classification.

The gauge measures ONE thing: how many fixes an agent ships silently that the
public benchmark's own hidden reference tests say are wrong. The classification
below is deliberately conservative so the scary number can't be inflated:

  - shipped_correct       agent produced a patch; reference tests pass.
  - silent_false_accept   agent produced a patch it reported as done; the hidden
                          reference tests FAIL. This is the number that matters.
  - abstained             agent produced no patch. Honest non-answer, NOT a
                          false-accept. It is never counted as one.
  - apply_failed          a patch was produced but did not apply cleanly. A
                          format/infra failure, not a silent wrong ship.
  - unscored              no evaluation report for this instance (not run yet).

Ground truth is always the benchmark's shipped reference tests (`resolved` in a
SWE-bench report). The gauge never synthesizes an acceptance test — that is a
different tool. See WHERE_THIS_STOPS.md.
"""
from dataclasses import dataclass, field
from typing import Optional

# Public benchmarks that ship per-instance ground-truth tests. The gauge only
# runs against these by construction — never against code with no reference
# tests (that would require synthesizing an oracle; see WHERE_THIS_STOPS.md).
KNOWN_DATASETS = {
    "SWE-bench/SWE-bench_Lite": "test",
    "SWE-bench/SWE-bench_Verified": "test",
    "SWE-bench/SWE-bench": "test",
}

SHIPPED_CORRECT = "shipped_correct"
SILENT_FALSE_ACCEPT = "silent_false_accept"
ABSTAINED = "abstained"
APPLY_FAILED = "apply_failed"
UNSCORED = "unscored"

OUTCOMES = [SHIPPED_CORRECT, SILENT_FALSE_ACCEPT, APPLY_FAILED, ABSTAINED, UNSCORED]


@dataclass
class Disposition:
    instance_id: str
    repo: str = ""
    has_patch: bool = False
    patch_applied: Optional[bool] = None
    resolved: Optional[bool] = None
    outcome: str = UNSCORED
    note: str = ""


def classify(instance_id, repo, model_patch, report):
    """Fold a prediction + its evaluation report into a single honest outcome.

    `report` is the per-instance dict from a SWE-bench report.json, or None if
    the instance has not been evaluated yet.

    When a report exists it is authoritative about whether a patch was actually
    evaluated (`patch_is_None` / `patch_exists`) — NOT the prediction file's
    `model_patch`, which can be blanked/scrubbed in a published kit while the
    report still reflects a real, applied patch. The prediction's emptiness is
    used only as a fallback when the report is missing or silent on the point.
    """
    pred_has_patch = bool((model_patch or "").strip())

    if report is None:
        if pred_has_patch:
            return Disposition(instance_id, repo, True, None, None, UNSCORED,
                               "no evaluation report found")
        return Disposition(instance_id, repo, False, None, None, ABSTAINED,
                           "agent produced no patch")

    # Report present: let it decide whether a patch was evaluated at all.
    patch_is_none = report.get("patch_is_None")
    patch_exists = report.get("patch_exists")
    if patch_is_none is True or patch_exists is False:
        evaluated_patch = False
    elif patch_is_none is False or patch_exists is True:
        evaluated_patch = True
    else:
        evaluated_patch = pred_has_patch  # report silent → trust the prediction

    if not evaluated_patch:
        return Disposition(instance_id, repo, False, None, None, ABSTAINED,
                           "no patch evaluated")

    applied = report.get("patch_successfully_applied")
    resolved = bool(report.get("resolved"))
    if applied is False:
        return Disposition(instance_id, repo, True, False, resolved, APPLY_FAILED,
                           "patch did not apply cleanly")
    if resolved:
        return Disposition(instance_id, repo, True, applied, True, SHIPPED_CORRECT)
    return Disposition(instance_id, repo, True, applied, False, SILENT_FALSE_ACCEPT,
                       "reported done; hidden reference tests fail")


def tally(dispositions):
    counts = {o: 0 for o in OUTCOMES}
    for d in dispositions:
        counts[d.outcome] += 1
    ships = counts[SHIPPED_CORRECT] + counts[SILENT_FALSE_ACCEPT]
    return counts, ships
