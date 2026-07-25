"""What the frame is made of — disclosure, not sampling (contract §5, §6).

The contract fixes the frame as "top 50 per language group by stars". In this
window that phrase quietly means something specific: a large share of the
top-starred repositories in 2026 are AI or agent projects, and because those
repositories are unusually busy, their share of *pull request volume* is larger
still. A reader who is not told this has to guess it.

So the frame's composition is measured, published, and used for one extra cut of
the headline: the base rate in AI-adjacent repositories against the rest.

Two things this is careful about:

  * It is **not** the AI-versus-human comparison the contract refuses (§6). That
    one needs author attribution, which is unreliable. This is a property of the
    *repository*, taken from its own description and topics — no claim is made
    about who wrote any pull request.
  * The classifier is a published keyword pattern, deliberately crude so it can
    be read and disputed in one line. It over-counts: a repository whose
    description merely mentions a model or a chat feature lands in the AI bucket.
    The over-count direction is stated rather than tuned away.

Timing, for the record: this cut was added after the frame was built and before
any diff was fetched or scored. It cannot have been chosen to flatter a verdict
that did not exist yet.
"""
import json
import pathlib
import re
import urllib.request

from .gh import read_token

ART = pathlib.Path("study-artifacts")

# Published so it can be argued with. Word-boundary matches against
# "<full_name> <description> <topics>", case-insensitive.
AI_PATTERN = (
    r"\b(ai|a\.i\.|llm|llms|gpt|agent|agents|agentic|chatbot|copilot|"
    r"prompt|prompts|rag|inference|embedding|embeddings|transformer|"
    r"transformers|diffusion|openai|anthropic|claude|gemini|deepseek|qwen|"
    r"llama|mistral|ollama|vllm|langchain|mcp|assistant|coding-agent)\b"
)
AI = re.compile(AI_PATTERN, re.IGNORECASE)


def fetch_descriptions(frame, out_path=ART / "frame_descriptions.json"):
    """One request per framed repository, cached as its own artifact."""
    token, _ = read_token()
    out = {}
    for r in frame["included"]:
        name = r["full_name"]
        req = urllib.request.Request(
            f"https://api.github.com/repos/{name}",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json",
                     "User-Agent": "patchward-study-composition"})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
            out[name] = {"description": (d.get("description") or "").strip(),
                         "topics": d.get("topics") or []}
        except Exception as e:                                  # noqa: BLE001
            out[name] = {"description": "", "topics": [],
                         "error": f"{type(e).__name__}"}
    pathlib.Path(out_path).write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"descriptions: {len(out)} repositories -> {out_path}")
    return out


def is_ai_adjacent(full_name, meta):
    blob = f"{full_name} {meta.get('description', '')} {' '.join(meta.get('topics', []))}"
    return bool(AI.search(blob))


def classify(frame, descriptions):
    """Per-repository class plus frame-level shares."""
    classes, by_group, pr_ai, pr_all = {}, {}, 0, 0
    for r in frame["included"]:
        name = r["full_name"]
        ai = is_ai_adjacent(name, descriptions.get(name, {}))
        classes[name] = "ai-adjacent" if ai else "other"
        g = by_group.setdefault(r["group"], {"repos": 0, "ai": 0})
        g["repos"] += 1
        g["ai"] += 1 if ai else 0
        pr_all += r["merged_prs_in_window"]
        pr_ai += r["merged_prs_in_window"] if ai else 0

    return {
        "pattern": AI_PATTERN,
        "repo_classes": classes,
        "by_group": by_group,
        "repos_ai": sum(v["ai"] for v in by_group.values()),
        "repos_total": len(classes),
        "pr_volume_ai": pr_ai,
        "pr_volume_total": pr_all,
        "pr_volume_ai_share": (pr_ai / pr_all) if pr_all else None,
    }


def concentration(sample, top_n=10):
    """How much of the drawn sample comes from its busiest repositories.

    The draw is proportional to volume, which is what the contract says — but it
    means a handful of hyperactive repositories carry a large share of the
    sample, and the headline is partly a statement about them. Published so
    nobody has to reverse-engineer it from the PR list.
    """
    counts = {}
    for pr in sample["prs"]:
        counts[pr["full_name"]] = counts.get(pr["full_name"], 0) + 1
    total = sum(counts.values()) or 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:top_n]
    return {
        "drawn": total,
        "distinct_repositories": len(counts),
        "top": [{"full_name": n, "drawn": c, "share": c / total} for n, c in top],
        "top_share": sum(c for _, c in top) / total,
    }


def base_rate_by_class(rows, repo_classes):
    """Headline base rate split by repository class."""
    out = {}
    for r in rows:
        if r.get("disposition") != "analysed":
            continue
        cls = repo_classes.get(r["full_name"], "other")
        b = out.setdefault(cls, {"analysed": 0, "flagged": 0})
        b["analysed"] += 1
        b["flagged"] += 1 if (r.get("severity") or 0) >= 3 else 0
    for b in out.values():
        b["rate"] = b["flagged"] / b["analysed"] if b["analysed"] else None
    return out
