"""Read the public SWE-bench harness output — the ground truth.

The gauge does not decide correctness itself. It reads the per-instance
report.json that the public SWE-bench evaluation harness writes, and takes its
`resolved` flag as truth. That flag means: the instance's own hidden reference
tests (shipped with the benchmark) pass. No oracle is synthesized here.

Point --reports at either:
  - a folder of `<instance_id>.report.json` files (the layout patchward ships), or
  - a SWE-bench `logs/run_evaluation/<run_id>/<model>/` tree (report.json per dir).
Both are globbed for `*report.json` and merged.
"""
import glob
import json
import os


def load_reports(reports_dir):
    """Return {instance_id: report_fields_dict} from any report.json under dir."""
    reports = {}
    pattern = os.path.join(reports_dir, "**", "*report.json")
    for path in glob.glob(pattern, recursive=True):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        # SWE-bench report.json is {instance_id: {resolved, ...}}.
        for iid, fields in data.items():
            if isinstance(fields, dict) and "resolved" in fields:
                reports[iid] = fields
    return reports
