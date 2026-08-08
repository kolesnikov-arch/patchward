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

#: A single commit whose diff is larger than this is not read, and is counted
#: instead. These are vendored trees, generated lockfiles and checked-in build
#: output — nobody reviews them line by line and the view has nothing to say
#: about them, but pairing over a hunk that size is quadratic and on two of
#: these projects it exhausted memory.
#:
#: A byte cap rather than a time limit on purpose: a timeout excludes different
#: work on a faster machine, which would make this run unrepeatable, and an
#: exclusion rule that depends on the hardware is not a rule.
MAX_DIFF_BYTES = 1_000_000


def walk(repo):
    """Stream one commit at a time.

    The first version of this read the whole `git log -p` into a string and
    split it. That survived twelve repositories and then took 3 GB of memory on
    projects with large generated diffs, which makes a published script that
    nobody else can run. Reading line by line keeps one commit in memory at a
    time regardless of how big the history is.
    """
    proc = subprocess.Popen(
        ["git", "-C", repo, "log", "-p", "--unified=3", "--no-color",
         "--no-renames", f"--max-count={MAX_COMMITS}",
         f"--format={SEP}%H\x1f%s"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, errors="replace", bufsize=1)

    sha = subject = None
    body = []
    try:
        for line in proc.stdout:
            if line.startswith(SEP):
                if sha is not None:
                    yield sha, subject, "".join(body)
                header = line[len(SEP):].rstrip("\n")
                parts = (header.split("\x1f") + [""])[:2]
                sha, subject, body = parts[0][:10], parts[1], []
            elif sha is not None:
                body.append(line)
        if sha is not None:
            yield sha, subject, "".join(body)
    finally:
        proc.stdout.close()
        proc.wait()


def scan(path):
    commits = touched = flagged = bulk = oversized = 0
    sizes = []
    for _sha, _subject, diff in walk(path):
        if not diff.strip():
            continue
        commits += 1
        # Counted in the population, deliberately: dropping them from the
        # denominator would quietly change what every rate below is a rate of.
        if len(diff) > MAX_DIFF_BYTES:
            oversized += 1
            continue
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
        "summarised_as_bulk": bulk, "commits_too_large_to_read": oversized,
        "median_per_flagged": statistics.median(sizes) if sizes else None,
        "max_per_flagged": max(sizes) if sizes else None,
        "flagged_of_three_or_fewer": sum(1 for s in sizes if s <= 3),
    }


def main(base):
    repos = {}
    paths = sorted(glob.glob(os.path.join(base, "*.git")))
    for n, path in enumerate(paths, start=1):
        name = os.path.basename(path)[:-4].replace("_", "/", 1)
        # Progress on stderr so a long run is observable and stdout stays a
        # clean JSON document.
        print(f"[{n}/{len(paths)}] {name}", file=sys.stderr, flush=True)
        repos[name] = scan(path)

    tot = {k: sum(v[k] for v in repos.values())
           for k in ("commits", "touched_tests", "retracting",
                     "summarised_as_bulk", "flagged_of_three_or_fewer",
                     "commits_too_large_to_read")}
    tot["repositories"] = len(repos)
    print(json.dumps({"tool": "patchward-check 0.2.2",
                      "max_commits_per_repo": MAX_COMMITS,
                      "totals": tot, "by_repository": repos},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
