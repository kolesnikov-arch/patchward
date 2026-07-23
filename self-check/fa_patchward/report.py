"""Turn predictions + ground-truth reports into YOUR number.

Reads a SWE-bench-format predictions.jsonl and a folder of evaluation reports,
classifies every instance (see model.py), and writes:

  results.csv    one row per instance: patch? / applied? / resolved / outcome
  RESULTS.md     the headline number + disposition + exact 95% CI, human-readable
  summary.json   the same, machine-readable, for `fa-patchward verify`

The headline is a single figure: of the fixes your agent shipped (reported as
done), how many the benchmark's hidden tests say are wrong. Abstains and
apply-failures are reported separately and never folded into it.
"""
import csv
import json
import os

from .model import (ABSTAINED, APPLY_FAILED, SHIPPED_CORRECT,
                    SILENT_FALSE_ACCEPT, UNSCORED, classify, tally)
from .score import load_reports
from .stats import clopper_pearson


def _read_predictions(path):
    preds = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            preds[rec["instance_id"]] = rec
    return preds


def build_dispositions(predictions_path, reports_dir, ids=None):
    preds = _read_predictions(predictions_path)
    reports = load_reports(reports_dir)
    ids = ids or sorted(preds)
    disps = []
    for iid in ids:
        rec = preds.get(iid, {})
        repo = iid.split("__")[0] if "__" in iid else ""
        disps.append(classify(iid, repo, rec.get("model_patch", ""),
                              reports.get(iid)))
    return disps


def summarize(disps):
    counts, ships = tally(disps)
    k = counts[SILENT_FALSE_ACCEPT]
    lo, hi = clopper_pearson(k, ships) if ships else (0.0, 0.0)
    return {
        "counts": counts,
        "ships": ships,
        "silent_false_accept": k,
        "rate_of_ships": (k / ships) if ships else None,
        "ci95": [lo, hi],
        "total_instances": len(disps),
    }


def write_csv(disps, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance_id", "repo", "has_patch", "patch_applied",
                    "resolved", "outcome", "note"])
        for d in disps:
            w.writerow([d.instance_id, d.repo, d.has_patch, d.patch_applied,
                        d.resolved, d.outcome, d.note])


def render_md(disps, s, model_label):
    c, ships = s["counts"], s["ships"]
    k = s["silent_false_accept"]
    lo, hi = s["ci95"]
    rate = f"{s['rate_of_ships']:.1%}" if s["rate_of_ships"] is not None else "n/a"
    fa_ids = [d.instance_id for d in disps if d.outcome == SILENT_FALSE_ACCEPT]

    lines = [
        f"# Your silent-false-accept number — `{model_label}`",
        "",
        "> The diagnosis, not the cure. This measures how many wrong fixes your",
        "> agent ships **silently** when nothing is checking it. It does not gate",
        "> them — an independent verdict layer does that, and that is deliberately",
        "> not part of this tool. See WHERE_THIS_STOPS.md.",
        "",
        "## Headline",
        "",
        f"Run ungated on **{s['total_instances']}** frozen public-benchmark tasks, "
        f"your agent **shipped {ships}** fixes it reported as done.",
        "",
        f"### Of those, **{k}/{ships} = {rate}** were wrong — shipped silently.",
        "",
        f"Exact 95% CI (Clopper-Pearson): **[{lo:.1%}, {hi:.1%}]**.",
        "",
        "Ground truth = the benchmark's own hidden reference tests. Not this tool's",
        "opinion — the same public `resolved` flag anyone can recompute.",
        "",
        "## Full disposition",
        "",
        "| outcome | count | counts toward the number? |",
        "|---|---:|---|",
        f"| shipped_correct | {c[SHIPPED_CORRECT]} | denominator |",
        f"| **silent_false_accept** | **{c[SILENT_FALSE_ACCEPT]}** | **numerator** |",
        f"| apply_failed | {c[APPLY_FAILED]} | no (format/infra failure) |",
        f"| abstained | {c[ABSTAINED]} | no (honest non-answer) |",
        f"| unscored | {c[UNSCORED]} | no (not evaluated yet) |",
        "",
        "The number is silent_false_accept / (shipped_correct + silent_false_accept).",
        "Abstains and apply-failures are shown but never inflate it.",
        "",
    ]
    if fa_ids:
        lines += ["## The silent wrong ships", "",
                  "Each of these: your agent produced a patch, reported done, and the",
                  "hidden reference tests fail.", ""]
        lines += [f"- `{i}`" for i in fa_ids] + [""]
    lines += [
        "## Is this number honest?",
        "",
        "Only if you froze the task set **before** running (see selection.json) and",
        "did not reroll on a bad outcome. `fa-patchward verify` recomputes this from",
        "the raw reports so it can't drift from the evidence. Same discipline the",
        "reference result held itself to — do the same or the number is vanity.",
        "",
    ]
    return "\n".join(lines)


def report(predictions_path, reports_dir, out_dir, model_label, ids=None):
    os.makedirs(out_dir, exist_ok=True)
    disps = build_dispositions(predictions_path, reports_dir, ids)
    s = summarize(disps)

    write_csv(disps, os.path.join(out_dir, "results.csv"))
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"model_label": model_label, **s}, f, indent=2)
    md = render_md(disps, s, model_label)
    with open(os.path.join(out_dir, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write(md)

    # Compact ASCII summary to the console; RESULTS.md is the full deliverable.
    k, ships = s["silent_false_accept"], s["ships"]
    rate = f"{s['rate_of_ships']:.1%}" if s["rate_of_ships"] is not None else "n/a"
    lo, hi = s["ci95"]
    print(f"\n{model_label}: shipped {ships} fixes reported as done; "
          f"{k} were wrong -> {k}/{ships} = {rate} silent false-accept")
    print(f"  95% CI [{lo:.1%}, {hi:.1%}]  |  ground truth = benchmark reference tests")
    print(f"  disposition: {dict(s['counts'])}")
    print(f"wrote results.csv, summary.json, RESULTS.md -> {out_dir}")
    return s


def verify(out_dir, reports_dir, predictions_path, ids=None):
    """Recompute from raw reports and cross-check the shipped results.csv."""
    csv_path = os.path.join(out_dir, "results.csv")
    with open(csv_path, encoding="utf-8") as f:
        saved = {r["instance_id"]: r for r in csv.DictReader(f)}
    disps = build_dispositions(predictions_path, reports_dir, ids or list(saved))

    mismatches = 0
    for d in disps:
        row = saved.get(d.instance_id)
        if row is None or row["outcome"] != d.outcome:
            mismatches += 1
            print(f"  MISMATCH {d.instance_id}: csv={row and row['outcome']} "
                  f"recomputed={d.outcome}")
    s = summarize(disps)
    if mismatches:
        raise SystemExit(f"verify FAILED: {mismatches} outcome mismatch(es).")
    k, ships = s["silent_false_accept"], s["ships"]
    lo, hi = s["ci95"]
    print(f"verify OK: recomputed from reports matches results.csv "
          f"({len(disps)} instances).")
    print(f"silent false-accept: {k}/{ships}  95% CI [{lo:.1%}, {hi:.1%}]")
    return s
