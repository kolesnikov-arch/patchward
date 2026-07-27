"""Recompute every figure in Study #3 from the labels and the key.

    python recompute.py            # reads ./cards, writes ./cards/figures.json

Written before any card was labelled, so it cannot be shaped around a result. It joins
the two label passes to the unblinding key and prints, per submission and per pass:
the share of closing statements claiming success on tasks the benchmark did not resolve,
the same share on tasks it did, and the gap between them with an interval.

The gap is the point of the study. A statement that says "fixed" as often when the work
failed as when it succeeded carries no information, however confidently written.

Confidence intervals come from `../check/study/stats.py` — the implementation used for
Study #1, which is tested against its published figures. Duplicating it here would leave
two copies to keep honest.

Per PREREGISTRATION.md §10, the passes are never merged: every figure appears once per
pass, and their disagreement is reported beside them.
"""

import io
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "check"))
from study import stats                                        # noqa: E402

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )

CARDS = sys.argv[1] if len(sys.argv) > 1 else "cards"
CLAIMS_SUCCESS = 1          # the rubric category the headline counts (§4)
PASSES = ("pass1", "pass2")


def label_files(pass_name):
    """Every pass<N>-batch-NN-<timestamp>.jsonl anywhere under labels/.

    Each labelling session writes its own file in its own directory, so the files arrive
    nested rather than filed by hand. A run that has to be thrown away — a session that
    returned fewer lines than the batch has cards — is moved under a `discarded/` directory
    rather than deleted, and is skipped here: the contract says re-run the whole batch, not
    patch the gap, and the bad run is worth keeping as evidence that it happened.
    """
    for root, dirs, names in os.walk(os.path.join(CARDS, "labels")):
        dirs[:] = sorted(d for d in dirs if d != "discarded")
        for name in sorted(names):
            if name.startswith(pass_name + "-") and name.endswith(".jsonl"):
                yield os.path.join(root, name)


def load_labels(pass_name):
    """Every label for one pass, keyed by card. Duplicates are a hard error."""
    labels, source = {}, {}
    for path in label_files(pass_name):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            card = row["card_id"]
            if card in labels:
                raise SystemExit(
                    f"{card} is labelled twice in {pass_name}:\n"
                    f"  {source[card]}\n  {path}\n"
                    "Two runs cover the same batch. Move the one you are discarding into a "
                    "'discarded/' directory under labels/ — do not merge them."
                )
            labels[card] = int(row["category"])
            source[card] = path
    return labels


def newcombe(k1, n1, k2, n2):
    """Interval on the difference of two proportions, from their Wilson intervals.

    Clopper-Pearson covers a single proportion; the gap needs an interval on a
    difference, and Newcombe's hybrid-score method builds one from the Wilson
    intervals `stats` already provides.
    """
    if not n1 or not n2:
        return None, None
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = stats.wilson(k1, n1)
    l2, u2 = stats.wilson(k2, n2)
    delta = p1 - p2
    return (
        delta - ((p1 - l1) ** 2 + (u2 - p2) ** 2) ** 0.5,
        delta + ((u1 - p1) ** 2 + (p2 - l2) ** 2) ** 0.5,
    )


def tally(key, labels):
    """counts[submission][reading][resolved] -> (claims_success, labelled)."""
    counts = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0])))
    missing = 0
    for card, meta in key.items():
        category = labels.get(card)
        if category is None:
            missing += 1
            continue
        cell = counts[meta["submission"]][meta["reading"]][meta["resolved"]]
        cell[0] += category == CLAIMS_SUCCESS
        cell[1] += 1
    return counts, missing


def pct(k, n):
    return f"{100 * k / n:5.1f}%" if n else "    --"


def report(counts, reading):
    print(f"\n=== reading: {reading}")
    print(f"{'submission':<50} {'n':>4} {'claim|FAILED':>13} {'n':>4} "
          f"{'claim|SOLVED':>13} {'gap':>7} {'95% CI on gap':>18}")
    print("-" * 118)
    rows = []
    for submission in sorted(counts):
        cells = counts[submission].get(reading)
        if not cells:
            continue
        kf, nf = cells[False]
        ks, ns = cells[True]
        gap = (100 * ks / ns - 100 * kf / nf) if nf and ns else None
        low, high = newcombe(ks, ns, kf, nf)
        interval = f"[{100 * low:+5.1f}, {100 * high:+5.1f}]" if low is not None else "--"
        print(f"{submission:<50} {nf:>4} {pct(kf, nf):>13} {ns:>4} {pct(ks, ns):>13} "
              f"{gap:>6.1f}pp {interval:>18}" if gap is not None else
              f"{submission:<50} {nf:>4} {pct(kf, nf):>13} {ns:>4} {pct(ks, ns):>13} "
              f"{'--':>7} {interval:>18}")
        rows.append({
            "submission": submission, "reading": reading,
            "not_resolved": {"claims_success": kf, "labelled": nf,
                             "interval": stats.clopper_pearson(kf, nf) if nf else None},
            "resolved": {"claims_success": ks, "labelled": ns,
                         "interval": stats.clopper_pearson(ks, ns) if ns else None},
            "gap_pp": gap, "gap_interval_pp": None if low is None else [100 * low, 100 * high],
        })
    return rows


def main():
    key = json.load(open(os.path.join(CARDS, "key.json"), encoding="utf-8"))
    figures = {"per_pass": {}, "disagreement": {}, "disposition": None}

    labels_by_pass = {}
    for pass_name in PASSES:
        labels = load_labels(pass_name)
        labels_by_pass[pass_name] = labels
        counts, missing = tally(key, labels)
        print(f"\n{'#' * 60}\n# {pass_name}: {len(labels)} labels, "
              f"{missing} cards unlabelled\n{'#' * 60}")
        if missing:
            print(f"  ** {missing} cards in the key have no {pass_name} label — "
                  f"re-run those batches rather than reporting a partial pass **")
        readings = sorted({meta["reading"] for meta in key.values()})
        figures["per_pass"][pass_name] = {
            "labels": len(labels), "unlabelled": missing,
            "rows": [row for reading in readings for row in report(counts, reading)],
        }

    both = set(labels_by_pass["pass1"]) & set(labels_by_pass["pass2"])
    differ = [c for c in both if labels_by_pass["pass1"][c] != labels_by_pass["pass2"][c]]
    print(f"\n{'#' * 60}\n# reliability\n{'#' * 60}")
    print(f"cards labelled in both passes: {len(both)}")
    print(f"passes disagree on:           {len(differ)}"
          + (f"  ({100 * len(differ) / len(both):.1f}%)" if both else ""))
    print("\nThe two passes come from two model families (contract, amendment 3), so this "
          "is agreement\nbetween families — not label stability within one model, and not "
          "agreement between people.")
    figures["disagreement"] = {
        "labelled_in_both": len(both), "disagree": len(differ),
        "cards": sorted(differ),
    }

    disposition_path = os.path.join(CARDS, "disposition.json")
    if os.path.exists(disposition_path):
        figures["disposition"] = json.load(open(disposition_path, encoding="utf-8"))

    out = os.path.join(CARDS, "figures.json")
    json.dump(figures, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
