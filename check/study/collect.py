"""Fetch diffs and score them (contract §2, §3).

Fetching and scoring are separate passes over the same cache on purpose: the
diffs are collected once, and every later scoring run reads the same bytes.
That is what lets `verify` recompute the published numbers without the network,
and what stops a rerun from quietly picking up a different diff.

Nothing is ever dropped silently. A PR that cannot be fetched, or that exceeds
the pre-registered size limit, becomes a disposition row with a reason.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from patchward_check import analyse            # noqa: E402
from patchward_check.report import as_dict     # noqa: E402

from .gh import NotAvailable, RateLimited      # noqa: E402

MAX_CHANGED_LINES = 5000       # contract §3
CACHE = pathlib.Path("cache/diffs")


def _cache_file(pr):
    owner_repo = pr["full_name"].replace("/", "__")
    return CACHE / f"{owner_repo}__{pr['number']}.diff"


def fetch(client, sample_path="study-artifacts/sample.json"):
    """Download every drawn PR's diff into the cache. Resumable."""
    sample = json.loads(pathlib.Path(sample_path).read_text(encoding="utf-8"))
    CACHE.mkdir(parents=True, exist_ok=True)
    errors_path = pathlib.Path("study-artifacts/fetch_errors.jsonl")
    errors_path.parent.mkdir(parents=True, exist_ok=True)

    have = failed = 0
    with errors_path.open("a", encoding="utf-8") as errlog:
        for i, pr in enumerate(sample["prs"], 1):
            dest = _cache_file(pr)
            if dest.exists():
                have += 1
                continue
            owner, repo = pr["full_name"].split("/", 1)
            try:
                diff = client.pull_diff(owner, repo, pr["number"])
            except NotAvailable as e:
                failed += 1
                errlog.write(json.dumps({**pr, "error": str(e)}) + "\n")
                errlog.flush()
                continue
            except RateLimited as e:
                print(f"\nstopped at {i}/{len(sample['prs'])}: {e}")
                print("re-run to resume — the cache is preserved")
                break
            dest.write_text(diff, encoding="utf-8", newline="")
            have += 1
            if i % 50 == 0:
                print(f"  {i}/{len(sample['prs'])} "
                      f"({have} cached, {failed} unavailable)")

    print(f"\nfetch: {have} diffs cached, {failed} unavailable "
          f"(logged to {errors_path})")
    return have, failed


def _changed_lines(diff_text):
    n = 0
    for line in diff_text.splitlines():
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            n += 1
    return n


def score(sample_path="study-artifacts/sample.json",
          out_path="study-artifacts/results.jsonl"):
    """Score every cached diff. One row per drawn PR, always."""
    sample = json.loads(pathlib.Path(sample_path).read_text(encoding="utf-8"))
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    counts = {}
    with out.open("w", encoding="utf-8") as f:
        for pr in sample["prs"]:
            row = {"full_name": pr["full_name"], "number": pr["number"],
                   "group": pr["group"], "user": pr.get("user", ""),
                   "title": pr.get("title", "")}
            path = _cache_file(pr)

            if not path.exists():
                row.update(disposition="excluded",
                           reason="diff-unavailable", verdict=None)
            else:
                diff = path.read_text(encoding="utf-8", errors="replace")
                n = _changed_lines(diff)
                row["changed_lines"] = n
                if n > MAX_CHANGED_LINES:
                    row.update(disposition="excluded",
                               reason=f"oversize:{n}", verdict=None)
                elif n == 0:
                    row.update(disposition="excluded",
                               reason="empty-diff", verdict=None)
                else:
                    res = analyse(diff)
                    d = as_dict(res, f"{pr['full_name']}#{pr['number']}")
                    row.update(disposition="analysed", reason=None,
                               verdict=d["verdict"], severity=d["severity"],
                               kinds=sorted({x["kind"] for x in d["findings"]}),
                               source_files=len(d["source_files"]),
                               test_files=len(d["test_files"]),
                               new_tests=d["new_tests"],
                               new_assertions=d["new_assertions"])

            key = row["verdict"] or row["reason"]
            counts[key] = counts.get(key, 0) + 1
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    total = sum(counts.values())
    print(f"score: {total} rows -> {out_path}")
    for k in sorted(counts, key=lambda k: -counts[k]):
        print(f"  {k:<22} {counts[k]:>5}")
    if total != sample["actual_n"]:
        print(f"  ERROR: {total} rows for {sample['actual_n']} drawn PRs — "
              f"the disposition table must sum to the draw")
    return counts
