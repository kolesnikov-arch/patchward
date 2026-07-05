"""Reproduce the held-out task selection (50 tasks, seed=50).

Adapted for this kit from the internal selection script: identical rules and
seed; the only change is that the prior-instance exclusion list is read from
`prior_instance_ids.txt` (shipped here) instead of the internal task files.

Selection rules (fixed before the run; see PREREGISTRATION.md §5):
  - Source: SWE-bench Lite, test split (300 instances).
  - EXCLUDE psf/requests (its 2014-era suite calls the public httpbin.org,
    which returns 503 today -> even the reference solution cannot resolve).
  - EXCLUDE heavy compiled repos (matplotlib, scikit-learn, astropy, seaborn)
    -> slow builds, outside the hermetic pure-Python pool.
  - EXCLUDE every instance ever used to develop or tune the instrument
    (`prior_instance_ids.txt`, 63 ids) -> the held-out is disjoint from all
    tuning data.
  - random.sample with seed=50 from the remaining pool (176 instances).

Run:  pip install datasets && python select_held_out.py
Expected output: the 50 ids in held_out_task_ids.txt, overlap with prior = 0,
by repo: django 23, sympy 16, sphinx 6, xarray 3, pylint 2.
"""
import os
import random

from datasets import load_dataset

SEED = 50
N = 50
HEAVY = {"matplotlib", "scikit-learn", "astropy", "seaborn"}
HERE = os.path.dirname(os.path.abspath(__file__))


def repo_key(row):
    return row["repo"].split("/")[-1].lower()


def excluded(row):
    return "requests" in row["repo"].lower() or repo_key(row) in HEAVY


def main():
    with open(os.path.join(HERE, "prior_instance_ids.txt"), encoding="utf-8") as f:
        used = {line.strip() for line in f if line.strip()}
    ds = load_dataset("SWE-bench/SWE-bench_Lite", split="test")
    rows = [dict(r) for r in ds]
    pool = [r for r in rows if not excluded(r) and r["instance_id"] not in used]
    random.seed(SEED)
    sample = sorted(random.sample(pool, N), key=lambda r: r["instance_id"])

    with open(os.path.join(HERE, "held_out_task_ids.txt"), encoding="utf-8") as f:
        published = [line.strip() for line in f if line.strip()]

    ids = [r["instance_id"] for r in sample]
    by_repo = {}
    for r in sample:
        by_repo[repo_key(r)] = by_repo.get(repo_key(r), 0) + 1

    print(f"prior (excluded): {len(used)}")
    print(f"pool after exclusions: {len(pool)} / {len(rows)}")
    print(f"selected {len(ids)} (seed={SEED}); overlap with prior: "
          f"{len(set(ids) & used)} (must be 0)")
    print("by repo:", dict(sorted(by_repo.items(), key=lambda kv: -kv[1])))
    print("matches published held_out_task_ids.txt:", ids == published)


if __name__ == "__main__":
    main()
