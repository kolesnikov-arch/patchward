"""Freeze the task set you will measure yourself on — before you look at any number.

Two ways to get a task list:

  1. Seeded sample from a public benchmark (needs `datasets`):
         fa-patchward select --dataset SWE-bench/SWE-bench_Lite --n 50 --seed 50
     Records dataset, split, seed, n, and any exclusions into selection.json so
     the choice is reproducible and can't be quietly reshuffled after seeing the
     result. This mirrors the pre-registration discipline of the reference run.

  2. Bring your own frozen ids:
         fa-patchward select --from-ids my_tasks.txt
     Use this if you already have a held-out list you committed to.

Note: this samples YOUR OWN frozen set. It intentionally does not reuse anyone
else's published held-out ids — measuring yourself on a set someone tuned against
is how a self-check lies to you.
"""
import json
import os
import random
from datetime import datetime, timezone

from .model import KNOWN_DATASETS


def _load_ids(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def from_ids(ids_path, out_dir):
    ids = _load_ids(ids_path)
    provenance = {"source": "from-ids", "ids_file": os.path.abspath(ids_path),
                  "n": len(ids)}
    return _write(ids, provenance, out_dir)


def seeded_sample(dataset, n, seed, out_dir, exclude_path=None, split=None):
    if dataset not in KNOWN_DATASETS:
        raise SystemExit(
            f"'{dataset}' is not a known public ground-truth benchmark.\n"
            f"fa-patchward only measures against sets that ship reference tests: "
            f"{', '.join(sorted(KNOWN_DATASETS))}.\n"
            f"Measuring your private repo would need a synthesized oracle — that "
            f"is deliberately not this tool (see WHERE_THIS_STOPS.md).")
    try:
        from datasets import load_dataset
    except ImportError:
        raise SystemExit("Seeded sampling needs `datasets`: pip install "
                         "'fa-patchward[select]'  (or use --from-ids).")

    split = split or KNOWN_DATASETS[dataset]
    rows = [dict(r) for r in load_dataset(dataset, split=split)]
    excluded = set(_load_ids(exclude_path)) if exclude_path else set()
    pool = [r for r in rows if r["instance_id"] not in excluded]
    if n > len(pool):
        raise SystemExit(f"asked for {n} but only {len(pool)} instances in pool.")

    random.seed(seed)
    sample = sorted(random.sample(pool, n), key=lambda r: r["instance_id"])
    ids = [r["instance_id"] for r in sample]

    by_repo = {}
    for r in sample:
        key = r["repo"].split("/")[-1].lower()
        by_repo[key] = by_repo.get(key, 0) + 1

    provenance = {"source": "seeded-sample", "dataset": dataset, "split": split,
                  "seed": seed, "n": n, "pool_size": len(pool),
                  "excluded": len(excluded), "by_repo": by_repo}
    return _write(ids, provenance, out_dir)


def _write(ids, provenance, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    provenance["frozen_at"] = datetime.now(timezone.utc).isoformat()
    tasks_path = os.path.join(out_dir, "tasks.txt")
    sel_path = os.path.join(out_dir, "selection.json")
    with open(tasks_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ids) + "\n")
    with open(sel_path, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)
    print(f"froze {len(ids)} tasks -> {tasks_path}")
    if "by_repo" in provenance:
        print("by repo:", provenance["by_repo"])
    print(f"provenance -> {sel_path}")
    print("\nCommit these two files BEFORE you run, so your number is honest.")
    return ids
