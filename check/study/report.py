"""Reporting (contract §5) and the blind-review export (contract §4).

Every commitment in §5 is a function here, and `render` emits all of them
whether they flatter the instrument or not. The order is deliberate: the
disposition table and the false-positive review come before the headline is
allowed to mean anything.
"""
import collections
import datetime
import json
import pathlib
import random

from .stats import clopper_pearson, wilson

HIGH_KINDS = ("REWRITTEN_EXPECTATION", "DELETED_TEST", "SUPPRESSED")
SIZE_BUCKETS = [(0, 20), (21, 100), (101, 500), (501, 2000), (2001, 5000)]
REVIEW_N = 60
SEED = 25


def load(path="study-artifacts/results.jsonl"):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _pct(x, n):
    return f"{100.0 * x / n:.1f}%" if n else "—"


def _ci_str(k, n):
    lo, hi = clopper_pearson(k, n)
    return f"[{lo * 100:.1f}%, {hi * 100:.1f}%]"


def summarize(rows):
    analysed = [r for r in rows if r["disposition"] == "analysed"]
    excluded = [r for r in rows if r["disposition"] == "excluded"]
    n = len(analysed)
    high = [r for r in analysed if r.get("severity", 0) >= 3]

    by_kind = collections.Counter()
    for r in high:
        for k in r.get("kinds", []):
            if k in HIGH_KINDS:
                by_kind[k] += 1

    by_group = {}
    for g in sorted({r["group"] for r in analysed}):
        rows_g = [r for r in analysed if r["group"] == g]
        k_g = sum(1 for r in rows_g if r.get("severity", 0) >= 3)
        by_group[g] = {"n": len(rows_g), "high": k_g,
                       "ci": _ci_str(k_g, len(rows_g))}

    by_size = {}
    for lo, hi in SIZE_BUCKETS:
        rows_b = [r for r in analysed if lo <= r.get("changed_lines", 0) <= hi]
        k_b = sum(1 for r in rows_b if r.get("severity", 0) >= 3)
        by_size[f"{lo}-{hi}"] = {"n": len(rows_b), "high": k_b,
                                 "rate": (k_b / len(rows_b)) if rows_b else None}

    lo, hi = clopper_pearson(len(high), n) if n else (0.0, 0.0)
    return {
        "drawn": len(rows),
        "analysed": n,
        "excluded": len(excluded),
        "excluded_reasons": dict(collections.Counter(
            r["reason"] for r in excluded)),
        "verdicts": dict(collections.Counter(
            r["verdict"] for r in analysed)),
        "high_severity": len(high),
        "rate": (len(high) / n) if n else None,
        "ci95_clopper_pearson": [lo, hi],
        "ci95_wilson": list(wilson(len(high), n)) if n else [0.0, 0.0],
        "by_finding_kind": dict(by_kind),
        "by_language_group": by_group,
        "by_diff_size": by_size,
    }


def export_review_sample(rows, out_path="study-artifacts/review_sample.jsonl",
                         n_each=REVIEW_N, seed=SEED, client=None):
    """Contract §4: flagged + unflagged, shuffled, verdict stripped.

    Rubric category 2 ("justified expectation change") turns on whether the
    pull request *states* an intentional behaviour change — so the reviewer
    needs the PR description, not just the diff. If a client is supplied, the
    descriptions are fetched here, once, and stored alongside; the reviewer then
    works entirely offline and never has to open GitHub, which is both faster
    and one less way to accidentally see something that unblinds a case.
    """
    analysed = [r for r in rows if r["disposition"] == "analysed"]
    flagged = [r for r in analysed if r.get("severity", 0) >= 3]
    unflagged = [r for r in analysed if r.get("severity", 0) < 3]

    rng = random.Random(seed)
    take = min(n_each, len(flagged))
    if take < n_each:
        print(f"  note: only {take} flagged PRs exist — reviewing all of them, "
              f"matched with {take} unflagged (contract §4)")

    picked = (rng.sample(sorted(flagged, key=lambda r: (r['full_name'], r['number'])), take)
              + rng.sample(sorted(unflagged, key=lambda r: (r['full_name'], r['number'])), take))
    rng.shuffle(picked)

    key = {}
    with open(out_path, "w", encoding="utf-8") as f:
        for i, r in enumerate(picked, 1):
            rid = f"R{i:03d}"
            key[rid] = {"full_name": r["full_name"], "number": r["number"],
                        "was_flagged": r.get("severity", 0) >= 3,
                        "kinds": r.get("kinds", [])}

            body = ""
            if client is not None:
                owner, repo = r["full_name"].split("/", 1)
                try:
                    data, _ = client.get_json(
                        f"/repos/{owner}/{repo}/pulls/{r['number']}")
                    body = (data.get("body") or "")[:4000]
                except Exception as e:      # never let one 404 stop the export
                    body = f"[description unavailable: {e}]"

            # Everything the reviewer sees. Note what is absent: verdict,
            # severity, kinds, was_flagged.
            f.write(json.dumps({
                "review_id": rid,
                "url": f"https://github.com/{r['full_name']}/pull/{r['number']}",
                "title": r.get("title", ""),
                "body": body,
                "changed_lines": r.get("changed_lines"),
                "_diff_ref": f"{r['full_name'].replace('/', '__')}__{r['number']}.diff",
                "classification": "",      # 1..5 per the rubric — fill in
                "note": "",
            }, ensure_ascii=False) + "\n")

    keypath = pathlib.Path(out_path).with_name("review_key.json")
    keypath.write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(f"review sample: {len(picked)} PRs -> {out_path}")
    print(f"  the unblinding key is {keypath} — do not open it until the "
          f"classifications are filled in and committed")
    print(f"  review them with: python -m study serve")
    return picked


def score_review(review_path="study-artifacts/review_sample.jsonl",
                 key_path="study-artifacts/review_key.json"):
    """Fold the filled-in review against the key. Categories 2,3,4 = false positive."""
    with open(review_path, encoding="utf-8") as f:
        reviews = {r["review_id"]: r
                   for r in (json.loads(l) for l in f if l.strip())}
    key = json.loads(pathlib.Path(key_path).read_text(encoding="utf-8"))

    tally = collections.Counter()
    tp = fp = undecidable = missed = no_test_change = contradiction = 0
    for rid, k in key.items():
        cls = str(reviews.get(rid, {}).get("classification", "")).strip()
        if not cls:
            continue
        tally[f"{'flagged' if k['was_flagged'] else 'unflagged'}:{cls}"] += 1
        if k["was_flagged"]:
            if cls == "1":
                tp += 1
            elif cls in ("2", "3", "4"):
                fp += 1
            elif cls == "5":
                undecidable += 1
            elif cls == "6":
                # The instrument only fires on test edits, so "no test change"
                # on a flagged PR means one of the two is wrong. Surfaced, not
                # absorbed into either column.
                contradiction += 1
        elif cls == "1":
            missed += 1          # retracted evidence the tool did not flag
        elif cls == "6":
            no_test_change += 1  # nothing to judge; not a miss, not a success

    judged = tp + fp
    return {
        "reviewed": sum(1 for rid in key
                        if str(reviews.get(rid, {}).get("classification", "")).strip()),
        "true_positive": tp, "false_positive": fp,
        "undecidable": undecidable,
        "missed_by_tool": missed,
        "no_test_change": no_test_change,
        "flagged_but_no_test_change": contradiction,
        "precision": (tp / judged) if judged else None,
        "precision_ci95": _ci_str(tp, judged) if judged else None,
        "rubric_tally": dict(tally),
    }


def pass_agreement(a_path, b_path):
    """Per-card agreement between two independent classification passes (§4).

    This is label *stability*, not inter-rater agreement between people, and the
    contract says so in those words. With no human arm it is the only reliability
    signal the design can produce, so it is computed and published rather than
    left as a reassuring adjective.
    """
    def _load_pass(p):
        with open(p, encoding="utf-8") as f:
            return {r["review_id"]: str(r.get("classification", "")).strip()
                    for r in (json.loads(l) for l in f if l.strip())}

    a, b = _load_pass(a_path), _load_pass(b_path)
    both = [rid for rid in a if a[rid] and b.get(rid)]
    agree = [rid for rid in both if a[rid] == b[rid]]
    disagree = sorted(rid for rid in both if a[rid] != b[rid])
    return {
        "compared": len(both),
        "agree": len(agree),
        "disagree": len(disagree),
        "agreement_rate": (len(agree) / len(both)) if both else None,
        "disagreeing_cards": {rid: [a[rid], b[rid]] for rid in disagree},
    }


def render(summary, review=None, instrument_commit="UNPINNED"):
    n, k = summary["analysed"], summary["high_severity"]
    lo, hi = summary["ci95_clopper_pearson"]
    d = datetime.date.today().isoformat()

    L = [
        f"# Study #1 results — how often do merged pull requests rewrite the tests that judge them?",
        "",
        f"**Run date: {d}. Instrument: `patchward-check` @ `{instrument_commit}`.**",
        f"Reported against [the pre-registered contract](PREREGISTRATION_PR_STUDY.md), "
        f"committed before collection began.",
        "",
        "## 1. Disposition first (contract §5.2)",
        "",
        "| | count |",
        "|---|---|",
        f"| Drawn | **{summary['drawn']}** |",
        f"| Analysed | {summary['analysed']} |",
        f"| Excluded | {summary['excluded']} |",
    ]
    for reason, c in sorted(summary["excluded_reasons"].items(),
                            key=lambda kv: -kv[1]):
        L.append(f"| &nbsp;&nbsp;— {reason} | {c} |")
    L += ["", f"Excluded + analysed = {summary['excluded'] + summary['analysed']}; "
              f"drawn = {summary['drawn']}. These must be equal.", ""]

    L += [
        "## 2. Headline base rate",
        "",
        f"> Of **{n}** analysed merged pull requests, **{k}** ({_pct(k, n)}) were "
        f"flagged at high severity — the change replaced, deleted, or suppressed "
        f"an existing test expectation.",
        "",
        f"95% CI (Clopper-Pearson, exact): **[{lo * 100:.1f}%, {hi * 100:.1f}%]**  ",
        f"Wilson, for comparison: [{summary['ci95_wilson'][0] * 100:.1f}%, "
        f"{summary['ci95_wilson'][1] * 100:.1f}%]",
        "",
        "**This is not a defect rate.** It counts a structural property of a diff. "
        "Whether any of these changes was wrong is not measured here (contract §6).",
        "",
        "## 3. Which rule fired (contract §5.5)",
        "",
        "| finding | count | share of analysed |",
        "|---|---|---|",
    ]
    for kind in HIGH_KINDS:
        c = summary["by_finding_kind"].get(kind, 0)
        L.append(f"| `{kind}` | {c} | {_pct(c, n)} |")

    L += ["", "## 4. By language group (contract §5.3)", "",
          "| group | analysed | flagged | rate | 95% CI |", "|---|---|---|---|---|"]
    for g, s in summary["by_language_group"].items():
        L.append(f"| {g} | {s['n']} | {s['high']} | {_pct(s['high'], s['n'])} "
                 f"| {s['ci']} |")
    L += ["", "> Path heuristics are best validated on Python and least on Go — "
              "stated in the contract (§7) before these numbers existed.", ""]

    L += ["## 5. Flag rate against diff size (contract §5.6)", "",
          "| changed lines | analysed | flagged | rate |", "|---|---|---|---|"]
    for bucket, s in summary["by_diff_size"].items():
        rate = f"{s['rate'] * 100:.1f}%" if s["rate"] is not None else "—"
        L.append(f"| {bucket} | {s['n']} | {s['high']} | {rate} |")
    L += ["", "> If the rate climbs steeply with size, the headline is partly a "
              "proxy for *large pull request* and should be read that way.", ""]

    comp = summary.get("frame_composition")
    if comp:
        L += ["## 5b. What the frame is actually made of (disclosure)", "",
              f"The contract fixes the frame as *top 50 per language group by "
              f"stars*. In this window that means "
              f"**{comp['repos_ai']} of {comp['repos_total']} repositories** are AI "
              f"or agent projects by the published keyword pattern, and because "
              f"those repositories are unusually busy they carry "
              f"**{comp['pr_volume_ai_share'] * 100:.0f}% of the merged-PR volume** "
              f"the sample is drawn from.", ""]
        L += ["| group | repositories | AI-adjacent |", "|---|---|---|"]
        for g, v in sorted(comp["by_group"].items()):
            L.append(f"| {g} | {v['repos']} | {v['ai']} |")
        L += ["",
              "The classifier is a keyword pattern, published here so it can be "
              "disputed, and it **over-counts** — a repository whose description "
              "merely mentions a model or a chat feature lands in the AI bucket:",
              "", f"```\n{comp['pattern']}\n```", "",
              "This is a property of the *repository*, not of who wrote any pull "
              "request. It is not the AI-versus-human comparison the contract "
              "declines (§6): that needs author attribution, which is unreliable. "
              "This cut was added after the frame was built and **before any diff "
              "was fetched or scored**, so it cannot have been chosen to flatter a "
              "verdict that did not exist yet.", ""]

        brc = summary.get("base_rate_by_repo_class") or {}
        if brc:
            L += ["| repository class | analysed | flagged | rate |",
                  "|---|---|---|---|"]
            for cls in sorted(brc):
                b = brc[cls]
                rate = f"{b['rate'] * 100:.1f}%" if b["rate"] is not None else "—"
                L.append(f"| {cls} | {b['analysed']} | {b['flagged']} | {rate} |")
            L += ["", "> If these two rates differ materially, the headline is "
                      "partly a statement about which repositories dominate the "
                      "frame, and should be read that way.", ""]

        conc = summary.get("sample_concentration")
        if conc:
            L += [f"**Concentration.** The draw is proportional to volume, as the "
                  f"contract specifies, so the sample is not spread evenly: "
                  f"{conc['drawn']} pull requests come from "
                  f"{conc['distinct_repositories']} repositories, and the busiest "
                  f"ten supply **{conc['top_share'] * 100:.0f}%** of them.", "",
                  "| repository | drawn | share |", "|---|---|---|"]
            for t in conc["top"]:
                L.append(f"| {t['full_name']} | {t['drawn']} | "
                         f"{t['share'] * 100:.1f}% |")
            L.append("")

    L += ["## 6. Blind review — the false-positive number (contract §4, §5.4)", ""]
    if not review or not review.get("reviewed"):
        L += ["**Not yet performed.** Until it is, the headline above says nothing "
              "about whether the instrument is useful — only about how often it "
              "fires. This section is the one that decides the former.", ""]
    else:
        L += [
            f"Reviewed blind: **{review['reviewed']}** pull requests "
            f"(flagged and unflagged, shuffled, verdicts hidden).",
            "",
            "| | count |", "|---|---|",
            f"| Flagged & confirmed *retracted evidence* | {review['true_positive']} |",
            f"| Flagged & judged legitimate (**false positive**) | {review['false_positive']} |",
            f"| Flagged & undecidable from the diff | {review['undecidable']} |",
            f"| **Not** flagged but retracted evidence (**missed**) | {review['missed_by_tool']} |",
            f"| No test change in the pull request at all | {review.get('no_test_change', 0)} |",
            f"| Flagged although no test changed (contradiction — a bug) | "
            f"{review.get('flagged_but_no_test_change', 0)} |",
            "",
            f"**Precision: {review['precision'] * 100:.1f}%** "
            f"{review['precision_ci95']}" if review.get("precision") is not None
            else "Precision: not computable.",
            "",
            "Undecidable cases are never resolved in the instrument's favour "
            "(contract §4).", "",
            "**These labels are LLM-rated, not human-rated** (contract §4, §6). The "
            "judge and the instrument read the same diff, so their errors correlate, "
            "which biases precision *upward*. Discount accordingly; the base rate "
            "above carries no such caveat. All 120 cards, both passes and their "
            "reasons ship with these results so the labels can be re-rated.", "",
        ]
        pa = summary.get("pass_agreement")
        if pa and pa.get("compared"):
            L += [
                f"Two independent passes over the same {pa['compared']} cards agreed "
                f"on **{pa['agree']}** and differed on **{pa['disagree']}** "
                f"({pa['agreement_rate'] * 100:.1f}% stable). This measures label "
                f"stability, not agreement between people — the study has no human "
                f"arm and does not claim one.", "",
            ]

    L += ["## 7. Reproducing this", "",
          "```bash", "python -m study verify", "```", "",
          "Recomputes every figure above from `results.jsonl` and fails loudly on "
          "any mismatch. The repository frame, the drawn PR list, and the per-PR "
          "verdicts are all in `study-artifacts/`.", ""]
    return "\n".join(L)
