"""Rendering. Three shapes: terminal, JSON, and a Markdown PR comment.

The wording is load-bearing. This tool must never read as "your code is wrong"
— it does not know that. It reports one structural fact: the change edited the
tests that judge it. Every renderer restates the limitation.
"""
import json

from .detect import Result

ICON = {"clean": "\U0001f7e2", "note": "⚪", "review": "\U0001f7e1",
        "self-graded": "\U0001f534"}

HEADLINE = {
    "clean": "no self-grading detected",
    "note": "tests changed alongside source",
    "review": "tests moved, no new evidence added",
    "self-graded": "this change rewrote the tests that judge it",
}

DISCLAIMER = (
    "This does not mean the change is wrong. It means its evidence is not "
    "independent of it: the same change authored both the fix and the "
    "expectation it is measured against."
)


def _samples(f, indent):
    return "".join(f"\n{indent}{s.strip()[:110]}" for s in f.samples)


def text(res: Result, label: str = "diff", quiet: bool = False) -> str:
    if res.verdict == "clean":
        return "" if quiet else f"{ICON['clean']} {label}: {HEADLINE['clean']}"

    lines = [f"{ICON[res.verdict]} {label}: {HEADLINE[res.verdict]}"]
    for f in res.findings:
        lines.append(f"   [{f.level:<6}] {f.kind}  — {f.path}")
        lines.append(f"      {f.message}")
        if f.samples:
            lines.append("      evidence:" + _samples(f, "        "))
    if res.worst >= 2:
        lines.append(f"\n   {DISCLAIMER}")
    return "\n".join(lines)


def markdown(res: Result, label: str = "this pull request") -> str:
    if res.verdict == "clean":
        return (f"{ICON['clean']} **patchward check** — no self-grading "
                f"detected in {label}.")

    out = [f"{ICON[res.verdict]} **patchward check** — {HEADLINE[res.verdict]}",
           ""]
    for f in res.findings:
        out.append(f"**`{f.kind}`** · _{f.level}_ · `{f.path}`  ")
        out.append(f"{f.message}")
        if f.samples:
            out.append("")
            out.append("```diff")
            out += [f"-{s.strip()[:110]}" for s in f.samples]
            out.append("```")
        out.append("")
    out += ["---",
            f"> {DISCLAIMER}",
            ">",
            "> `patchward check` is a flag, not a gate. It reads the diff only "
            "— no tests are run, nothing is blocked."]
    return "\n".join(out)


def as_dict(res: Result, label: str = "diff") -> dict:
    return {
        "label": label,
        "verdict": res.verdict,
        "severity": res.worst,
        "source_files": res.source_files,
        "test_files": res.test_files,
        "new_tests": res.new_tests,
        "new_assertions": res.new_assertions,
        "findings": [
            {"kind": f.kind, "level": f.level, "path": f.path,
             "message": f.message, "samples": [s.strip() for s in f.samples]}
            for f in res.findings
        ],
    }


def as_json(res: Result, label: str = "diff") -> str:
    return json.dumps(as_dict(res, label), indent=2, ensure_ascii=False)
