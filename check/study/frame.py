"""Build and freeze the repository frame (contract §3).

Top 50 per language group by stars — Python, JavaScript/TypeScript, Go — for
150 repositories total, with every exclusion recorded and published alongside
the inclusions. An exclusion list nobody can see is an exclusion list nobody
can check.
"""
import datetime
import json
import re
import time

from .gh import Client

LANGUAGE_GROUPS = {
    "python": ["python"],
    "js-ts": ["javascript", "typescript"],
    "go": ["go"],
}
PER_GROUP = 50
MIN_MERGED_PRS = 100
WINDOW = ("2026-01-01", "2026-06-30")

# Objective, stated exclusion rule for repositories that are not really
# codebases. Applied to name + description, case-insensitive. Kept crude on
# purpose: a rule you can read in one line is auditable; a classifier is not.
NON_CODE = re.compile(
    r"\b(awesome|awesome-\w+|cheat-?sheets?|roadmaps?|tutorials?|courses?|"
    r"handbooks?|guides?|books?|interview|questions?|curriculum|learning|"
    r"resources?|collections?|lists?|papers?|datasets?|wiki|docs?|"
    r"documentation|examples?|demos?|boilerplates?|templates?|starter)\b",
    re.IGNORECASE,
)
# Candidates are pulled deeper than PER_GROUP because exclusions thin the pool.
CANDIDATE_PAGES = 3


def _merged_pr_query(full_name):
    return (f"repo:{full_name} is:pr is:merged "
            f"merged:{WINDOW[0]}..{WINDOW[1]}")


def _classify(repo):
    """Return an exclusion reason, or None to keep."""
    if repo.get("fork"):
        return "fork"
    if repo.get("archived"):
        return "archived"
    if repo.get("mirror_url"):
        return "mirror"
    text = f"{repo.get('name', '')} {repo.get('description') or ''}"
    m = NON_CODE.search(text)
    if m:
        return f"non-code:{m.group(0).lower()}"
    return None


def build(client: Client, out_path="study-artifacts/frame.json", per_group=None):
    """Build the frame. `per_group` overrides the contract size for smoke runs.

    A smoke run exists because the alternative is discovering that the live API
    path is broken at hour three of a real collection. Anything built with
    per_group != PER_GROUP is marked `smoke: true` and must not be reported.
    """
    per_group = per_group or PER_GROUP
    included, excluded = [], []

    for group, languages in LANGUAGE_GROUPS.items():
        candidates = []
        for lang in languages:
            candidates += client.search_repos(
                f"language:{lang} stars:>1000 is:public archived:false",
                pages=CANDIDATE_PAGES)
        # Deduplicate, then rank by stars across the whole group.
        seen, ranked = set(), []
        for r in sorted(candidates, key=lambda r: -r.get("stargazers_count", 0)):
            if r["full_name"] in seen:
                continue
            seen.add(r["full_name"])
            ranked.append(r)

        kept = 0
        for repo in ranked:
            if kept >= per_group:
                break
            reason = _classify(repo)
            if reason:
                excluded.append({"full_name": repo["full_name"], "group": group,
                                 "stars": repo.get("stargazers_count"),
                                 "reason": reason})
                continue

            n = client.search_issues_count(_merged_pr_query(repo["full_name"]))
            if n < MIN_MERGED_PRS:
                excluded.append({"full_name": repo["full_name"], "group": group,
                                 "stars": repo.get("stargazers_count"),
                                 "reason": f"too-few-merged-prs:{n}"})
                continue

            included.append({
                "full_name": repo["full_name"], "group": group,
                "language": (repo.get("language") or "").lower(),
                "stars": repo.get("stargazers_count"),
                "merged_prs_in_window": n,
                "default_branch": repo.get("default_branch"),
            })
            kept += 1
            print(f"  [{group}] {repo['full_name']:<45} "
                  f"{repo.get('stargazers_count'):>7} stars  {n:>5} merged PRs")
            time.sleep(1)

        if kept < per_group:
            print(f"  WARNING: group {group} yielded only {kept}/{per_group} "
                  f"repositories — reported as a shortfall, not topped up")

    frame = {
        "contract": "PREREGISTRATION_PR_STUDY.md",
        "built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "window": {"from": WINDOW[0], "to": WINDOW[1]},
        "smoke": per_group != PER_GROUP,
        "rules": {
            "per_group": per_group,
            "min_merged_prs": MIN_MERGED_PRS,
            "language_groups": LANGUAGE_GROUPS,
            "non_code_pattern": NON_CODE.pattern,
        },
        "included": included,
        "excluded": excluded,
        "totals": {
            "included": len(included),
            "excluded": len(excluded),
            "merged_prs_available": sum(r["merged_prs_in_window"]
                                        for r in included),
        },
    }

    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(frame, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nframe: {len(included)} repositories, {len(excluded)} excluded "
          f"-> {out_path}")
    print(f"       {frame['totals']['merged_prs_available']} merged PRs available")
    return frame
