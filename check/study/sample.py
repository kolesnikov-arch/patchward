"""Draw the PR sample (contract §3) — seeded, stratified, and frozen.

The draw happens once, before any diff is fetched and before any verdict
exists. `sample.json` is the artifact that makes the study checkable: anyone
with the frame and the seed reproduces exactly this list.

GitHub's search API returns at most 1000 results per query, and says nothing when
a query has more. Listing a busy repository by month therefore yields the
earliest 1000 merged PRs of each month and silently discards the rest — which is
a systematic bias, not a sample. (Measured on the first smoke run: 47.5% of the
population lost that way.) So each window is probed for its total first and split
in half recursively, down to single days if needed, until every sub-window fits
under the cap. Whatever still does not fit is written to `population_meta.json`
and printed. Nothing is dropped quietly.
"""
import datetime
import json
import pathlib
import random

SEED = 25
TARGET_N = 3000
SEARCH_CAP = 1000       # GitHub's hard limit on results returned per search query


def _query(repo, d_from, d_to):
    return f"repo:{repo} is:pr is:merged merged:{d_from}..{d_to}"


def _halve(d_from, d_to):
    """Split an inclusive date range into two inclusive halves."""
    a = datetime.date.fromisoformat(d_from)
    b = datetime.date.fromisoformat(d_to)
    mid = a + (b - a) // 2
    return ((a.isoformat(), mid.isoformat()),
            ((mid + datetime.timedelta(days=1)).isoformat(), b.isoformat()))


def _enumerate_window(client, repo, d_from, d_to, emit, truncated):
    """Enumerate one date range, subdividing until it fits under the search cap."""
    total = client.search_issues_count(_query(repo, d_from, d_to))
    if total == 0:
        return 0

    if total > SEARCH_CAP and d_from != d_to:
        left, right = _halve(d_from, d_to)
        return (_enumerate_window(client, repo, left[0], left[1], emit, truncated)
                + _enumerate_window(client, repo, right[0], right[1], emit, truncated))

    if total > SEARCH_CAP:      # one single day over the cap: cannot split further
        truncated.append({"from": d_from, "to": d_to, "total_count": total,
                          "retrievable": SEARCH_CAP})
        print(f"    ! {repo} {d_from}: {total} merged PRs in a single day, only "
              f"{SEARCH_CAP} retrievable — recorded as a shortfall, not dropped")

    return sum(1 for item in client.search_issues(_query(repo, d_from, d_to))
               if emit(item))


def enumerate_prs(client, frame, out_path="study-artifacts/population.jsonl"):
    """List every merged PR in the window for every framed repository."""
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    window = frame["window"]
    seen = set()
    meta = {"window": window, "search_cap": SEARCH_CAP, "repos": []}

    with p.open("w", encoding="utf-8") as out:
        for repo in frame["included"]:
            name, group = repo["full_name"], repo["group"]

            def emit(item, _name=name, _group=group):
                key = (_name, item["number"])
                if key in seen:
                    return False
                seen.add(key)
                out.write(json.dumps({
                    "full_name": _name,
                    "group": _group,
                    "number": item["number"],
                    "title": item.get("title", "")[:200],
                    "user": (item.get("user") or {}).get("login", ""),
                    "created_at": item.get("created_at"),
                }, ensure_ascii=False) + "\n")
                return True

            truncated = []
            found = _enumerate_window(client, name, window["from"], window["to"],
                                      emit, truncated)
            expected = repo.get("merged_prs_in_window")
            meta["repos"].append({"full_name": name,
                                  "frame_total_count": expected,
                                  "enumerated": found,
                                  "truncated_windows": truncated})
            drift = ("" if expected in (None, found)
                     else f"  (frame counted {expected})")
            print(f"  {name:<45} {found:>5} merged PRs enumerated{drift}")

    meta["complete"] = all(not r["truncated_windows"] for r in meta["repos"])
    (p.parent / "population_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\npopulation: {len(seen)} PRs -> {out_path}")
    print(f"accounting -> {p.parent / 'population_meta.json'}"
          + ("" if meta["complete"] else "   *** disclosed shortfalls inside"))
    return out_path


def draw(population_path="study-artifacts/population.jsonl",
         out_path="study-artifacts/sample.json", target_n=TARGET_N, seed=SEED):
    """Stratified draw by language group, proportional to available volume."""
    with open(population_path, encoding="utf-8") as f:
        pop = [json.loads(l) for l in f if l.strip()]
    # Sort first: the draw must not depend on file order or API response order.
    pop.sort(key=lambda r: (r["group"], r["full_name"], r["number"]))

    by_group = {}
    for r in pop:
        by_group.setdefault(r["group"], []).append(r)

    total = len(pop)
    rng = random.Random(seed)
    drawn, allocation = [], {}

    # Largest-remainder allocation so the strata sum exactly to target_n.
    raw = {g: target_n * len(rows) / total for g, rows in by_group.items()}
    base = {g: int(v) for g, v in raw.items()}
    remainder = target_n - sum(base.values())
    for g, _ in sorted(raw.items(), key=lambda kv: -(kv[1] - int(kv[1]))):
        if remainder <= 0:
            break
        base[g] += 1
        remainder -= 1

    for group in sorted(by_group):
        rows = by_group[group]
        n = min(base[group], len(rows))
        allocation[group] = {"available": len(rows), "drawn": n}
        drawn += rng.sample(rows, n)

    drawn.sort(key=lambda r: (r["group"], r["full_name"], r["number"]))

    sample = {
        "contract": "PREREGISTRATION_PR_STUDY.md",
        "drawn_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "seed": seed,
        "target_n": target_n,
        "actual_n": len(drawn),
        "population_size": total,
        "allocation": allocation,
        "prs": drawn,
    }
    pathlib.Path(out_path).write_text(
        json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"sample: {len(drawn)} PRs from a population of {total} "
          f"(seed {seed}) -> {out_path}")
    for g, a in sorted(allocation.items()):
        print(f"  {g:<8} {a['drawn']:>5} drawn of {a['available']:>6} available")
    if len(drawn) < target_n:
        print(f"  SHORTFALL: {target_n - len(drawn)} — reported, not substituted")
    return sample
