"""Run the retracted-expectation view over the drawn repositories.

    pip install patchward-check==0.2.2
    python check/field-run/draw.py | awk '{print $2}' | while read r; do
      git clone --bare --depth 250 --single-branch \
        "https://github.com/$r.git" "clones/$(echo $r | tr / _).git"
    done
    python check/field-run/scan.py clones > results.json

Bare clones on purpose: this reads history, never a working tree, and a working
tree is what fails on Windows path limits for a couple of these repositories.
"""
import glob
import json
import os
import statistics
import subprocess
import sys

from patchward_check.retracted import extract

SEP = "\x1epw\x1e"
MAX_COMMITS = 250


def walk(repo):
    out = subprocess.run(
        ["git", "-C", repo, "log", "-p", "--unified=3", "--no-color",
         "--no-renames", f"--max-count={MAX_COMMITS}",
         f"--format={SEP}%H\x1f%s"],
        capture_output=True, text=True, errors="replace").stdout
    for chunk in out.split(SEP):
        if not chunk.strip():
            continue
        header, _, body = chunk.partition("\n")
        parts = (header.split("\x1f") + [""])[:2]
        yield parts[0][:10], parts[1], body


def scan(path):
    commits = touched = flagged = bulk = 0
    sizes = []
    for _sha, _subject, diff in walk(path):
        if not diff.strip():
            continue
        commits += 1
        r = extract(diff)
        if r.test_files:
            touched += 1
        if len(r):
            flagged += 1
            sizes.append(len(r))
            if any(i.kind == "bulk" for i in r.items):
                bulk += 1
    return {
        "commits": commits, "touched_tests": touched, "retracting": flagged,
        "summarised_as_bulk": bulk,
        "median_per_flagged": statistics.median(sizes) if sizes else None,
        "max_per_flagged": max(sizes) if sizes else None,
        "flagged_of_three_or_fewer": sum(1 for s in sizes if s <= 3),
    }


def main(base):
    repos = {}
    for path in sorted(glob.glob(os.path.join(base, "*.git"))):
        name = os.path.basename(path)[:-4].replace("_", "/", 1)
        repos[name] = scan(path)

    tot = {k: sum(v[k] for v in repos.values())
           for k in ("commits", "touched_tests", "retracting",
                     "summarised_as_bulk", "flagged_of_three_or_fewer")}
    tot["repositories"] = len(repos)
    print(json.dumps({"tool": "patchward-check 0.2.2",
                      "max_commits_per_repo": MAX_COMMITS,
                      "totals": tot, "by_repository": repos},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
