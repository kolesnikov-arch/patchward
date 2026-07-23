"""Run your agent, ungated, over the frozen task set -> predictions.jsonl.

The gauge does not know how your agent works. It talks to it through one tiny
contract (your adapter). For each task the gauge writes a JSON record to the
adapter's stdin and reads one JSON line from its stdout:

  in  -> {"instance_id", "repo", "base_commit", "problem_statement", ...}
         (whatever fields the benchmark provides for that instance)
  out <- {"instance_id": "...", "model_patch": "<unified diff, or empty>"}

An empty / missing model_patch means the agent abstained — an honest non-answer,
counted as such, never as a false-accept. A crash, a timeout, or unparseable
output is recorded as an abstain-with-error, and the run keeps going.

Ungated by design: the gauge ships whatever the agent returns, as-is. That is the
whole point — it measures what leaves when nothing is checking.
"""
import json
import subprocess

from .model import KNOWN_DATASETS

# Fields passed to the adapter when available from the dataset row.
_PASS_FIELDS = ("instance_id", "repo", "base_commit", "problem_statement",
                "hints_text", "version", "environment_setup_commit",
                "FAIL_TO_PASS", "PASS_TO_PASS")


def _task_records(ids, dataset):
    """Yield a task dict per id, enriched from the dataset if it is available."""
    rows_by_id = {}
    if dataset:
        try:
            from datasets import load_dataset
            split = KNOWN_DATASETS.get(dataset, "test")
            for r in load_dataset(dataset, split=split):
                if r["instance_id"] in set(ids):
                    rows_by_id[r["instance_id"]] = dict(r)
        except ImportError:
            print("note: `datasets` not installed; passing instance_id only. "
                  "Your adapter must fetch its own repo context.")
    for iid in ids:
        row = rows_by_id.get(iid, {})
        yield {k: row[k] for k in _PASS_FIELDS if k in row} or {"instance_id": iid}


def run(ids, adapter_cmd, out_path, model_label, dataset=None, timeout=1800):
    """Invoke the adapter per instance; write SWE-bench-format predictions.jsonl."""
    n_ship = n_abstain = n_error = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for task in _task_records(ids, dataset):
            iid = task["instance_id"]
            patch, note = _invoke(adapter_cmd, task, timeout)
            if note:
                n_error += 1
            elif patch.strip():
                n_ship += 1
            else:
                n_abstain += 1
            rec = {"instance_id": iid, "model_name_or_path": model_label,
                   "model_patch": patch}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            status = note or ("patch" if patch.strip() else "abstain")
            print(f"  {iid:40s} {status}")
    print(f"\nwrote {out_path}: {n_ship} patches, {n_abstain} abstains, "
          f"{n_error} errors")
    print("Now evaluate it with the public SWE-bench harness, then: fa-patchward report")


def _invoke(adapter_cmd, task, timeout):
    """Return (model_patch, note). note is '' on success, else an error tag."""
    try:
        proc = subprocess.run(adapter_cmd, input=json.dumps(task),
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "", "error:timeout"
    except (OSError, ValueError) as e:
        return "", f"error:launch:{type(e).__name__}"
    if proc.returncode != 0:
        return "", f"error:exit{proc.returncode}"
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return "", "error:bad-json"
    return data.get("model_patch", "") or "", ""
