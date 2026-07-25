"""Unified-diff parsing. No dependencies, no git required.

Deliberately small: the detector needs to know, per file, which content lines a
change *removed* and which it *added*, hunk by hunk. That distinction is the
whole basis of the analysis — an added assertion is new evidence, a removed one
is a retracted expectation, and only the diff structure tells them apart.
"""
import re
from dataclasses import dataclass, field
from typing import List

_GIT_HEADER = re.compile(r"^diff --git a/(?P<a>.+?) b/(?P<b>.+)$")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")
_DEV_NULL = "/dev/null"


@dataclass
class Hunk:
    """One @@ block. `removed`/`added` hold content only, prefix stripped."""
    removed: List[str] = field(default_factory=list)
    added: List[str] = field(default_factory=list)

    @property
    def is_pure_addition(self) -> bool:
        return bool(self.added) and not self.removed

    @property
    def is_replacement(self) -> bool:
        return bool(self.added) and bool(self.removed)


@dataclass
class FileDiff:
    path: str
    old_path: str = ""
    hunks: List[Hunk] = field(default_factory=list)
    is_new: bool = False
    is_deleted: bool = False

    @property
    def removed(self) -> List[str]:
        return [l for h in self.hunks for l in h.removed]

    @property
    def added(self) -> List[str]:
        return [l for h in self.hunks for l in h.added]


def parse(text: str) -> List[FileDiff]:
    """Parse a unified diff (git or plain) into FileDiff records."""
    files: List[FileDiff] = []
    cur: FileDiff = None
    hunk: Hunk = None
    in_hunk = False

    for raw in text.splitlines():
        m = _GIT_HEADER.match(raw)
        if m:
            cur = FileDiff(path=m.group("b"), old_path=m.group("a"))
            files.append(cur)
            hunk, in_hunk = None, False
            continue

        if raw.startswith("--- "):
            src = raw[4:].strip()
            if cur is None:  # plain diff with no `diff --git` header
                cur = FileDiff(path="")
                files.append(cur)
            cur.old_path = "" if src == _DEV_NULL else re.sub(r"^a/", "", src)
            cur.is_new = src == _DEV_NULL
            in_hunk = False
            continue

        if raw.startswith("+++ "):
            dst = raw[4:].strip()
            if cur is None:
                cur = FileDiff(path="")
                files.append(cur)
            if dst == _DEV_NULL:
                cur.is_deleted = True
                cur.path = cur.path or cur.old_path
            else:
                cur.path = re.sub(r"^b/", "", dst)
            in_hunk = False
            continue

        if _HUNK.match(raw):
            if cur is None:
                continue
            hunk = Hunk()
            cur.hunks.append(hunk)
            in_hunk = True
            continue

        if not in_hunk or hunk is None:
            continue

        if raw.startswith("\\"):          # "\ No newline at end of file"
            continue
        if raw.startswith("-"):
            hunk.removed.append(raw[1:])
        elif raw.startswith("+"):
            hunk.added.append(raw[1:])
        elif raw.startswith(" ") or raw == "":
            pass                          # context
        else:
            in_hunk = False               # left the hunk body

    return [f for f in files if f.path or f.old_path]
