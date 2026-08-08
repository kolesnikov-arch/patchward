"""What a change stops checking.

This is an extraction, not a judgement, and the distinction is the whole design.

`detect.py` answers "did this change edit its own judge" and hands back a
verdict. On a hand-labelled sample that verdict held about one time in fourteen
(`study-artifacts/APPENDIX_precision_by_class.md`), which is a usable ratio for
a list to skim and a terrible one for telling an author their pull request is
suspect.

This module answers a narrower question that needs no ratio at all: **which
expectations existed before this change and do not exist after it.** That is a
fact about the diff. A renaming refactor and a silently weakened test produce
the same list, and telling them apart takes a reviewer about two seconds — which
is the point. The two seconds are cheap; finding the three lines among four
hundred is not.

What counts as an expectation that stopped existing:

  * in a hunk that **replaces** content inside a test file, every replaced
    content line. Not "lines containing `assert`" — the sharpest real case we
    have rewrote the expected output literal inside an assertion and never
    touched the keyword. Keying on the keyword misses it.
  * in a hunk that only **deletes**, a removed line that is recognisably a test
    declaration or an assertion. Deleted imports and setup are not expectations.
  * a suppression marker (`skip`, `xfail`, `ignore`, `.only`) that was added:
    the test still exists and no longer runs.

A removed line that reappears among the file's additions was moved or
re-indented, not retracted, and is dropped — the same multiset rule the detector
uses, for the same reason it exists there.
"""
import difflib
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional

from .detect import ASSERTION, SUPPRESSION, TEST_DECL, _content, is_test_path
from .diff import FileDiff, parse

#: How similar a removed line and an added line must be before this module is
#: willing to show them as a before/after pair rather than as a bare removal.
#: Pairing is presentation only: the "was" line is exact either way.
PAIR_THRESHOLD = 0.6

#: Above this many retractions in one file, the file is summarised instead of
#: itemised. Measured, not guessed: across 950 commits of requests, flask and
#: fastapi the per-commit count ran to 69 and 102, and those were test rewrites
#: and dependency bumps rather than anything a reviewer wants line by line. A
#: list nobody reads is worse than a sentence they do.
ITEMISE_LIMIT = 8

#: Removed lines in one hunk above which pairing is not attempted at all and the
#: file is reported as a bulk rewrite directly.
#:
#: This is a stated rule, not a silent approximation. Pairing is quadratic, and
#: a hunk of this size would have to consist almost entirely of comment-only
#: changes to fall back under ITEMISE_LIMIT afterwards — but "almost entirely"
#: is not "provably never", so the behaviour is written down here rather than
#: claimed to be equivalent. Without it, a single vendored or generated diff
#: takes minutes and can exhaust memory.
PAIRING_LIMIT = 200

#: A hunk starting at or above this line is the head of the file — module
#: docstring, licence header, imports. Inside it, prose is prose.
HEAD_OF_FILE = 3

#: Characters that make a line code rather than prose. Used only at the head of
#: a file: deeper in, a line of prose may well be an expected output literal,
#: and the sharpest case this tool exists for is exactly that.
CODE_PUNCTUATION = set("=([{\"'\\:")

#: Lines that cannot be an expectation no matter which hunk they sit in.
#: Deliberately narrow. Note what is *not* here: string literals and bare
#: values, because the sharpest real case rewrote an expected output literal
#: with no assertion keyword anywhere near it. Excluding those to cut noise
#: would cut the one case this tool exists for.
NOT_AN_EXPECTATION = re.compile(
    r"^\s*("
    r"(from\s+\S+\s+)?import\s"                  # imports move constantly
    r"|@(?!.*\b(skip|skipif|xfail|ignore|only|disabled)\b)"  # non-suppression decorators
    r"|(#|//|/\*|\*/)"                           # comments, incl. `# type: ignore`
    r"|(async\s+)?def\s+(?!test)"                # helper defs; test defs handled above
    r"|@?(pytest\.)?fixture\b"
    r")",
    re.IGNORECASE,
)


@dataclass
class Retraction:
    path: str
    kind: str                      # "changed" | "removed" | "suppressed"
    was: Optional[str] = None
    now: Optional[str] = None


@dataclass
class Retractions:
    items: List[Retraction] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.items)

    @property
    def by_file(self):
        out = {}
        for r in self.items:
            out.setdefault(r.path, []).append(r)
        return out


def _pair(removed: List[str], added: List[str]):
    """Best-effort 1:1 match of removed lines to what replaced them.

    Greedy nearest-neighbour on string similarity. A wrong pairing shows a
    misleading "now" line beside a correct "was" line, so the threshold is set
    high enough that unrelated lines are reported as plain removals instead.
    """
    unused = list(added)
    for r in removed:
        rs = r.strip()
        lr = len(rs)
        best, best_ratio = None, 0.0
        for a in unused:
            as_ = a.strip()
            la = len(as_)
            # `ratio` is 2*matches/(la+lr) and matches cannot exceed the shorter
            # string, so this is an upper bound — computed with arithmetic
            # rather than difflib's own quick_ratio, whose call overhead cost
            # more than it saved. A candidate whose bound cannot beat the
            # incumbent cannot beat it on the real figure, so skipping changes
            # no result. Without it this loop is quadratic in the size of a
            # hunk and exhausts memory on generated diffs.
            if la + lr == 0 or 2.0 * min(la, lr) / (la + lr) <= best_ratio:
                continue
            ratio = difflib.SequenceMatcher(None, rs, as_).ratio()
            if ratio > best_ratio:
                best, best_ratio = a, ratio
        if best is not None and best_ratio >= PAIR_THRESHOLD:
            unused.remove(best)
            yield r, best
        else:
            yield r, None


def _looks_like_a_check(line: str) -> bool:
    return bool(ASSERTION.search(line) or TEST_DECL.match(line))


def _code_part(line: str) -> str:
    """The line with a trailing comment removed, whitespace squeezed.

    Only strips a marker that sits outside a string literal — counted by quotes
    rather than assumed. `assert x == "a#b"` must not lose its expected value:
    dropping a real retraction to tidy the output is the one trade this module
    is not allowed to make.
    """
    for i, ch in enumerate(line):
        if ch in "#/" and (ch == "#" or line[i:i + 2] == "//"):
            head = line[:i]
            if head.count('"') % 2 == 0 and head.count("'") % 2 == 0:
                return "".join(head.split())
    return "".join(line.split())


def _comment_only(was: str, now: str) -> bool:
    """True when the two lines differ only after a comment marker."""
    return was != now and _code_part(was) == _code_part(now) != ""


def _reflowed(removed: List[str], added: List[str]) -> bool:
    """True when the removed lines survive verbatim as re-wrapped added lines.

    Splitting one expression across lines, or joining it back, removes and adds
    lines whose *content* never changed. That is the same "moved, not retracted"
    rule the multiset check applies to whole lines, one level down.
    """
    if not removed or not added:
        return False
    flat_removed = "".join("".join(l.split()) for l in removed)
    flat_added = "".join("".join(l.split()) for l in added)
    return bool(flat_removed) and flat_removed in flat_added


def _file_retractions(fd: FileDiff) -> List[Retraction]:
    path = fd.path or fd.old_path

    if fd.is_new:
        return []                                  # a new test file adds, never retracts
    if fd.is_deleted:
        return [Retraction(path, "removed", was="the whole test file was deleted")]

    out: List[Retraction] = []

    survivors = Counter(a.strip() for a in fd.added)

    def moved_not_retracted(line: str) -> bool:
        key = line.strip()
        if survivors[key]:
            survivors[key] -= 1
            return True
        return False

    for h in fd.hunks:
        gone = [l for l in _content(h.removed)
                if not NOT_AN_EXPECTATION.match(l) and not moved_not_retracted(l)]
        kept_added = [l for l in _content(h.added)
                      if not NOT_AN_EXPECTATION.match(l)]

        # Reflow first, and on both sides unfiltered by anything below: this
        # asks whether the removed content survived, and narrowing one side
        # would make a survivor look like a casualty.
        if h.is_replacement and _reflowed(gone, kept_added):
            continue

        # The head of a file is its docstring and its imports. Found by running
        # this over its own repository, where editing the module docstring of a
        # test file was reported as three retracted expectations. The rule is
        # "prose is not code", not "the first lines do not count": an expected
        # literal sitting at the top of a file is still an expectation.
        if h.old_start and h.old_start <= HEAD_OF_FILE:
            gone = [l for l in gone
                    if _looks_like_a_check(l) or (set(l) & CODE_PUNCTUATION)]
        if not gone:
            continue
        if len(gone) > PAIRING_LIMIT:
            out += [Retraction(path, "removed", was=l) for l in gone]
        elif h.is_replacement:
            for was, now in _pair(gone, kept_added):
                if now and _comment_only(was, now):
                    continue
                out.append(Retraction(path, "changed" if now else "removed",
                                      was=was, now=now))
        else:
            out += [Retraction(path, "removed", was=l)
                    for l in gone if _looks_like_a_check(l)]

    out += [Retraction(path, "suppressed", now=l)
            for l in fd.added if SUPPRESSION.search(l)]

    if len(out) > ITEMISE_LIMIT:
        # A rewrite this size is a rewrite, not a retraction anyone can read
        # line by line. Say so, and say how big, rather than printing a wall.
        return [Retraction(path, "bulk", was=f"{len(out)} existing test lines "
                                             f"replaced or removed")]
    return out


def extract(diff_text: str, extra_test_globs: Optional[List[str]] = None) -> Retractions:
    """Pull the retracted expectations out of one unified diff."""
    res = Retractions()
    for fd in parse(diff_text):
        path = fd.path or fd.old_path
        if is_test_path(path, extra_test_globs):
            res.test_files.append(path)
            res.items += _file_retractions(fd)
        else:
            res.source_files.append(path)
    return res


# --------------------------------------------------------------------------
# Rendering. Deliberately plain: no severity, no colour, no verdict word.
# --------------------------------------------------------------------------

FOOTER = (
    "Extracted from the diff, not judged. These lines existed before this change "
    "and do not exist after it; whether that is right is yours to say. A rename, "
    "a deliberate behaviour change and a quietly weakened test all look the same "
    "here — telling them apart is a glance, finding them is not. Line-level only: "
    "it cannot know whether the behaviour is still covered somewhere else."
)

_VERB = {
    "changed": "changed",
    "removed": "removed",
    "suppressed": "no longer runs",
    "bulk": "a rewrite this size is not itemised",
}


def _headline(res: Retractions, label: str = "") -> str:
    n = len(res)
    what = "1 thing" if n == 1 else f"{n} things"
    subject = label or "This change"
    return f"{subject} stops checking {what}."


def markdown(res: Retractions, label: str = "", limit: int = 12) -> str:
    if not res.items:
        return ""
    lines = [f"**{_headline(res, label)}**", ""]
    shown = 0
    for path, items in res.by_file.items():
        if shown >= limit:
            break
        lines.append(f"`{path}`")
        lines.append("```diff")
        first = True
        for r in items:
            if shown >= limit:
                break
            if not first:
                lines.append("")          # one blank line keeps the pairs apart
            first = False
            if r.kind == "bulk":
                lines.append(f"! {r.was} — too large to itemise")
            else:
                if r.was:
                    lines.append(f"- {r.was.strip()}")
                if r.now:
                    lines.append(f"+ {r.now.strip()}")
            shown += 1
        lines.append("```")
        lines.append("")
    remaining = len(res) - shown
    if remaining > 0:
        lines.append(f"…and {remaining} more.")
        lines.append("")
    if res.source_files:
        n = len(res.source_files)
        lines.append(f"{n} source file{'' if n == 1 else 's'} changed in the "
                     f"same diff.")
        lines.append("")
    lines.append(f"<sub>{FOOTER}</sub>")
    return "\n".join(lines)


def text(res: Retractions, label: str = "", limit: int = 12) -> str:
    if not res.items:
        return ""
    out = [_headline(res, label), ""]
    shown = 0
    for path, items in res.by_file.items():
        if shown >= limit:
            break
        out.append(f"  {path}")
        for r in items:
            if shown >= limit:
                break
            if r.kind == "bulk":
                out.append(f"    {r.was} — too large to itemise")
            else:
                if r.was:
                    out.append(f"    was:  {r.was.strip()}")
                if r.now:
                    out.append(f"    now:  {r.now.strip()}")
                else:
                    out.append(f"          ({_VERB[r.kind]})")
            out.append("")
            shown += 1
    remaining = len(res) - shown
    if remaining > 0:
        out.append(f"  …and {remaining} more.")
        out.append("")
    if res.source_files:
        n = len(res.source_files)
        out.append(f"  {n} source file{'' if n == 1 else 's'} changed in the same diff.")
        out.append("")
    out.append(f"  {FOOTER}")
    return "\n".join(out)


def as_dict(res: Retractions, label: str = "") -> dict:
    return {
        "label": label,
        "stops_checking": len(res),
        "source_files": res.source_files,
        "test_files": res.test_files,
        "items": [{"path": r.path, "kind": r.kind, "was": r.was, "now": r.now}
                  for r in res.items],
        "note": FOOTER,
    }
