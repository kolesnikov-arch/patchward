"""patchward — a verdict layer for AI coding agents.

    patchward-check                        did this change edit its own tests?
    patchward-check --format retracted     what does this change stop checking?
    patchward-check scan                   the same, across your history

The check is the everyday command, and the default one: it reads a unified diff
(stdin, a file, or a git revision range) and answers one question — did this
change edit the tests that judge it? No tests are run. Nothing is blocked. It is
a flag, not a gate.

`--format retracted` answers a narrower question and gives no verdict at all: it
lists the expectations that existed before this change and do not exist after
it, as before/after pairs. That is a fact about the diff rather than a claim
about the author, which is why it is the format worth putting in front of a
human. It always exits 0.

`scan` points the same rule at your existing history, which is usually where the
first surprise lives.
"""
import argparse
import subprocess
import sys

from . import report as rep
from . import retracted as ret
from .detect import analyse

EXIT_CLEAN, EXIT_FINDINGS, EXIT_ERROR = 0, 1, 2
FAIL_LEVELS = {"never": 4, "high": 3, "medium": 2, "any": 1}


def _git(args, cwd=None):
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True,
                           text=True, errors="replace")
    except FileNotFoundError:
        sys.stderr.write("patchward: git not found on PATH\n")
        raise SystemExit(EXIT_ERROR)
    if p.returncode != 0:
        sys.stderr.write(f"patchward: git {' '.join(args)} failed:\n{p.stderr}")
        raise SystemExit(EXIT_ERROR)
    return p.stdout


def _read_diff(a):
    if a.diff:
        with open(a.diff, encoding="utf-8", errors="replace") as f:
            return f.read()
    if a.rev:
        return _git(["diff", "--unified=3", a.rev], cwd=a.repo)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    # Default to the working tree's staged+unstaged change, like a linter would.
    return _git(["diff", "--unified=3", "HEAD"], cwd=a.repo)


def cmd_check(a):
    diff = _read_diff(a)
    if not diff.strip():
        if not a.quiet:
            print("patchward: empty diff — nothing to check")
        return EXIT_CLEAN

    label = a.label or a.rev or a.diff or "working tree"

    # `retracted` is a different product from the rest of this command: an
    # extraction with no verdict in it, so it never fails a build and ignores
    # --fail-on. See retracted.py for why the two are kept apart.
    if a.format in ("retracted", "retracted-md", "retracted-json"):
        r = ret.extract(diff, a.test_glob)
        # No --label means no subject: "This change stops checking …" reads
        # better on a pull request than the path of a temporary file.
        shown_label = a.label or ""
        if a.format == "retracted-json":
            import json
            print(json.dumps(ret.as_dict(r, shown_label), indent=2, ensure_ascii=False))
        else:
            render = ret.markdown if a.format == "retracted-md" else ret.text
            out = render(r, shown_label)
            if out:
                print(out)
            elif not a.quiet:
                print("patchward: this change stops checking nothing")
        return EXIT_CLEAN

    res = analyse(diff, a.test_glob)

    if a.format == "json":
        print(rep.as_json(res, label))
    elif a.format == "markdown":
        print(rep.markdown(res, label))
    else:
        out = rep.text(res, label, quiet=a.quiet)
        if out:
            print(out)

    return (EXIT_FINDINGS if res.worst >= FAIL_LEVELS[a.fail_on]
            else EXIT_CLEAN)


# ASCII record separator: legal in a subprocess argument (NUL is not) and does
# not occur in commit subjects or diff bodies.
_SEP = "\x1epatchward\x1e"


def _walk_log(a):
    """Yield (sha, author, subject, diff) from ONE `git log -p` pass.

    Deliberately not one `git show` per commit: that is a subprocess per
    commit, and on a few hundred commits it turns "scan your history" into a
    coffee break. The whole selling point is that this is instant.
    """
    log = _git(["log", "-p", "--unified=3", "--no-color", "--no-renames",
                f"--max-count={a.max_count}",
                f"--format={_SEP}%H\x1f%an\x1f%s"]
               + ([a.range] if a.range else []), cwd=a.repo)

    for chunk in log.split(_SEP):
        if not chunk.strip():
            continue
        header, _, body = chunk.partition("\n")
        parts = (header.split("\x1f") + ["", ""])[:3]
        yield parts[0].strip(), parts[1], parts[2], body


def cmd_scan(a):
    rows, counts = [], {"clean": 0, "note": 0, "review": 0, "self-graded": 0}
    for sha, author, subject, diff in _walk_log(a):
        if a.author and a.author.lower() not in author.lower():
            continue
        if not diff.strip():
            continue
        res = analyse(diff, a.test_glob)
        counts[res.verdict] += 1
        if res.worst >= 2:
            rows.append((sha[:10], author, subject[:60], res))

    total = sum(counts.values())
    if a.format == "json":
        import json
        print(json.dumps({
            "commits_scanned": total, "counts": counts,
            "flagged": [{"commit": s, "author": au, "subject": sub,
                         **rep.as_dict(r, s)} for s, au, sub, r in rows],
        }, indent=2, ensure_ascii=False))
        return EXIT_FINDINGS if rows else EXIT_CLEAN

    for sha, author, subject, res in rows:
        print(f"{rep.ICON[res.verdict]} {sha}  {author[:18]:<18}  {subject}")
        for f in res.findings:
            if f.severity >= 2:
                print(f"      [{f.kind}] {f.path}")

    if total == 0:
        print("patchward: no commits matched")
        return EXIT_CLEAN

    flagged = counts["review"] + counts["self-graded"]
    print(f"\n— {total} commits scanned · "
          f"{counts['self-graded']} rewrote their own tests · "
          f"{counts['review']} moved tests without adding evidence · "
          f"{counts['note']} touched tests alongside source")
    print(f"— {flagged}/{total} would be flagged for review "
          f"({flagged / total:.1%})")
    print(f"\n  {rep.DISCLAIMER}")
    return EXIT_FINDINGS if flagged else EXIT_CLEAN


def build_parser():
    p = argparse.ArgumentParser(
        prog="patchward-check", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--repo", default=".", help="repository root")
        sp.add_argument("--test-glob", action="append", default=[],
                        metavar="REGEX",
                        help="extra regex marking a path as a test file "
                             "(repeatable)")
        sp.add_argument("--format",
                        choices=["text", "json", "markdown",
                                 "retracted", "retracted-md", "retracted-json"],
                        default="text")

    c = sub.add_parser("check", help="check one diff / revision range")
    common(c)
    src = c.add_mutually_exclusive_group()
    src.add_argument("--diff", help="unified diff file ('-' style stdin also works)")
    src.add_argument("--rev", metavar="REV",
                     help="git revision or range, e.g. HEAD~1 or main...HEAD")
    c.add_argument("--label", help="name to show in the report")
    c.add_argument("--fail-on", choices=list(FAIL_LEVELS), default="high",
                   help="exit 1 at this severity or above (default: high)")
    c.add_argument("--quiet", action="store_true",
                   help="print nothing when clean")
    c.set_defaults(func=cmd_check)

    s = sub.add_parser("scan", help="scan repository history")
    common(s)
    s.add_argument("--range", help="commit range, e.g. v1.0..HEAD")
    s.add_argument("--max-count", type=int, default=200)
    s.add_argument("--author", help="only commits whose author matches")
    s.set_defaults(func=cmd_scan)

    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # `check` is the default verb, so the command reads `patchward-check --rev X`
    # rather than repeating itself. `patchward-check check ...` still works.
    if not argv or argv[0] not in ("check", "scan", "-h", "--help"):
        argv.insert(0, "check")
    a = build_parser().parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
