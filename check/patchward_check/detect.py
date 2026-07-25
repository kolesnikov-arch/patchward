"""The detector: did this change edit the tests that are supposed to judge it?

One question, answered deterministically, with no oracle, no LLM, no execution.

It does NOT know whether a change is correct. It knows whether the evidence for
it is independent of it. Keeping those two apart is the entire point: a fix that
rewrites the test which used to fail is not proven, it is *unfalsified by
construction*.

Every rule below is a diff-structure fact, not a judgement:

  REWRITTEN_EXPECTATION  a hunk in a test file replaces existing content —
                         an expectation that used to hold was redefined.
  DELETED_TEST           a test case was removed outright.
  SUPPRESSED             skip / xfail / ignore / .only introduced.
  NO_NEW_EVIDENCE        source changed, tests touched, nothing new asserted.
  SELF_GRADED            source and its tests changed in the same diff.

Why "replaces existing content" and not "changed an assert line": the sharpest
real case we have (sympy 16503) rewrote the *expected output literal* inside an
assertion, never touching the word `assert`. Keying on the keyword misses it.
That miss was found by running against real data, not by reasoning.
"""
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional

from .diff import FileDiff, parse

# --------------------------------------------------------------------------
# Language surface. Conventions, not parsing — deliberately shallow and
# auditable. Anything ambiguous is resolved toward *not* flagging.
# --------------------------------------------------------------------------

TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|testing)/"
    r"|(^|/)test_[^/]+\.(py|rb)$"
    r"|(^|/)[^/]+_test\.(py|go|rb|dart)$"
    r"|(^|/)[^/]+_spec\.rb$"
    r"|(^|/)[^/]+\.(test|spec)\.(js|jsx|mjs|cjs|ts|tsx)$"
    r"|(^|/)[^/]*Tests?\.(java|kt|cs|scala|swift)$"
    r"|(^|/)conftest\.py$",
    re.IGNORECASE,
)

# A *declaration* of a test case.
TEST_DECL = re.compile(
    r"^\s*("
    r"(async\s+)?def\s+test\w*"                       # python
    r"|func\s+(Test|Benchmark|Fuzz|Example)\w*"       # go
    r"|(it|test|describe|context)\s*[.(]"             # js/ts/rspec
    r"|@Test\b|@ParameterizedTest\b"                  # java/kotlin
    r"|\[(Test|Fact|Theory|TestMethod)\]"             # c#
    r"|#\[test\]"                                     # rust
    r"|class\s+\w*Test\w*\b"                          # xunit-style classes
    r"|(it|specify|scenario)\s+['\"]"                 # rspec
    r")",
    re.IGNORECASE,
)

# A claim about behaviour.
ASSERTION = re.compile(
    r"\b("
    r"assert\w*"
    r"|expect\s*\("
    r"|should(Be|Equal|Not|Have|Throw|Raise)?\b"
    r"|raises\s*\(|pytest\.raises|assertRaises"
    r"|require\.\w+|\.Equal\(|\.NoError\(|\.True\(|\.False\("
    r"|verify\s*\(|Assert\.\w+"
    r"|t\.(Error|Fatal)f?\("
    r")",
    re.IGNORECASE,
)

SUPPRESSION = re.compile(
    r"(@(pytest\.mark\.)?(skip|skipif|xfail)\b"
    r"|@unittest\.skip|pytest\.skip\s*\(|self\.skipTest\s*\("
    r"|\b(it|describe|test|context)\.(skip|only)\s*\("
    r"|\bx(it|describe|test)\s*\("
    r"|t\.Skip(Now)?\s*\("
    r"|@(Ignore|Disabled)\b"
    r"|#\[ignore\]"
    r")",
    re.IGNORECASE,
)

# Lines that carry no expectation: blank, comment-only, bare punctuation.
NOISE = re.compile(r"^\s*($|#|//|/\*|\*|\*/|--\s|\}|\)|\]|,|'''|\"\"\")")

SEVERITY = {
    "REWRITTEN_EXPECTATION": 3,
    "DELETED_TEST": 3,
    "SUPPRESSED": 3,
    "NO_NEW_EVIDENCE": 2,
    "SELF_GRADED": 1,
}
LABEL = {3: "high", 2: "medium", 1: "info"}


@dataclass
class Finding:
    kind: str
    path: str
    message: str
    samples: List[str] = field(default_factory=list)

    @property
    def severity(self) -> int:
        return SEVERITY[self.kind]

    @property
    def level(self) -> str:
        return LABEL[self.severity]


@dataclass
class Result:
    findings: List[Finding] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    new_tests: int = 0
    new_assertions: int = 0

    @property
    def worst(self) -> int:
        return max((f.severity for f in self.findings), default=0)

    @property
    def verdict(self) -> str:
        return {0: "clean", 1: "note", 2: "review", 3: "self-graded"}[self.worst]

    def of(self, kind: str) -> List[Finding]:
        return [f for f in self.findings if f.kind == kind]


def is_test_path(path: str, extra: Optional[List[str]] = None) -> bool:
    if extra and any(re.search(p, path) for p in extra):
        return True
    return bool(TEST_PATH.search(path))


def _content(lines: List[str]) -> List[str]:
    return [l for l in lines if l.strip() and not NOISE.match(l)]


def analyse_file(fd: FileDiff) -> List[Finding]:
    """Rules that apply within a single test file's diff."""
    out: List[Finding] = []

    if fd.is_new:
        return out          # a brand-new test file adds evidence, never retracts

    if fd.is_deleted:
        return [Finding("DELETED_TEST", fd.path,
                        "test file deleted while source changed")]

    rewritten, removed_decls = [], []
    for h in fd.hunks:
        rm = _content(h.removed)
        if not rm:
            continue
        removed_decls += [l for l in rm if TEST_DECL.match(l)]
        if h.is_replacement:
            rewritten += rm

    # A removed line that reappears among the file's additions was not
    # retracted — it was moved or re-indented. Wrapping existing assertions in
    # try/finally, or re-indenting a block, is indistinguishable from rewriting
    # them when a hunk is read on its own. Found on real data (a refactor that
    # removed 14 assertion lines and added all 14 back verbatim inside a
    # try/finally, plus one NEW assertion, was reported as a rewrite).
    # A multiset, not a set: two removals matched by one addition still leave
    # one line genuinely gone.
    survivors = Counter(a.strip() for a in fd.added)

    def _kept_elsewhere(line: str) -> bool:
        key = line.strip()
        if survivors[key]:
            survivors[key] -= 1
            return True
        return False

    rewritten = [l for l in rewritten if not _kept_elsewhere(l)]

    if rewritten:
        asserty = [l for l in rewritten if ASSERTION.search(l)]
        detail = (f"{len(asserty)} of them carry an explicit assertion"
                  if asserty else
                  "none contain the word `assert` — the expected values "
                  "themselves were rewritten")
        out.append(Finding(
            "REWRITTEN_EXPECTATION", fd.path,
            f"{len(rewritten)} existing test line(s) replaced; {detail}. "
            f"An expectation that used to hold was redefined by the same "
            f"change it judges.",
            (asserty or rewritten)[:4],
        ))

    dropped = [l for l in removed_decls
               if not any(l.strip() == a.strip() for a in fd.added)]
    if dropped:
        out.append(Finding(
            "DELETED_TEST", fd.path,
            f"{len(dropped)} test case declaration(s) removed",
            dropped[:4],
        ))

    suppressed = [l for l in fd.added if SUPPRESSION.search(l)]
    if suppressed:
        out.append(Finding(
            "SUPPRESSED", fd.path,
            f"{len(suppressed)} skip/xfail/ignore/only marker(s) introduced",
            suppressed[:4],
        ))

    return out


def analyse(diff_text: str, extra_test_globs: Optional[List[str]] = None) -> Result:
    """Analyse one unified diff. This is the whole public surface."""
    res = Result()

    for fd in parse(diff_text):
        path = fd.path or fd.old_path
        if is_test_path(path, extra_test_globs):
            res.test_files.append(path)
            res.new_tests += sum(1 for l in fd.added if TEST_DECL.match(l))
            res.new_assertions += sum(1 for l in fd.added if ASSERTION.search(l))
            res.findings += analyse_file(fd)
        else:
            res.source_files.append(path)

    if not (res.source_files and res.test_files):
        # Tests-only or source-only change: nothing self-referential to report.
        res.findings = [f for f in res.findings if f.kind == "SUPPRESSED"]
        return res

    if not (res.new_tests or res.new_assertions) and not res.of("REWRITTEN_EXPECTATION"):
        res.findings.append(Finding(
            "NO_NEW_EVIDENCE", ", ".join(res.test_files[:3]),
            "test file(s) touched alongside source, but no new test case or "
            "assertion was added — the change moved its tests without adding "
            "evidence",
        ))

    res.findings.append(Finding(
        "SELF_GRADED", ", ".join(res.test_files[:3]),
        f"{len(res.source_files)} source file(s) and {len(res.test_files)} "
        f"test file(s) changed together — this change edited its own judge",
    ))

    res.findings.sort(key=lambda f: -f.severity)
    return res
