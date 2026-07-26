"""Build the labelling cards for Study #3, exactly as PREREGISTRATION.md specifies.

A card is one closing statement and nothing else. The submission it came from, the
instance id and — above all — whether the benchmark resolved that instance are written to
a separate key file that the labelling session never sees. Strata are shuffled together
so a labeller cannot infer the answer from position.

    python build_cards.py --dev     # plumbing check on the excluded development sample
    python build_cards.py --run     # the real draw; only after the contract is public

Outputs (into ./cards):
    cards.jsonl        card_id + text. This is what the labeller is given.
    key.json           card_id -> submission, instance, resolved, reading. Withheld.
    disposition.json   every candidate accounted for, by outcome.

Standard library only; needs network. Traces cache under ./trace-cache.
"""

import argparse
import hashlib
import json
import os
import random
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import adapters
from validate_adapters import BUCKET, DEV_INSTANCES, trace_keys, utf8_stdout

utf8_stdout()

RESULTS = (
    "https://raw.githubusercontent.com/SWE-bench/experiments/main/"
    "evaluation/verified/{}/results/results.json"
)
CACHE = "trace-cache"
SEED = 3
PER_STRATUM = 60

# PREREGISTRATION.md, amendment 4 (2026-07-27): a statement this long is not a closing
# statement, it is a slab of tool log, and no session can read it. Counted, never imputed.
MAX_STATEMENT = 20_000

# A labelling session has to hold the batch, the rubric and its own output at once, so a
# batch closes on whichever limit it reaches first. Batching is presentation only — the
# shuffle below fixes the order, and these bounds only decide where it is cut.
BATCH_CARDS = 80
BATCH_CHARS = 240_000

# §3: labelled only where the adapter can attribute the closing statement to the patch
# that was submitted. Warp summarises several attempts; Amazon Q names the candidate it
# submitted but does not number the narratives. Both are reported, neither is labelled.
NOT_ATTRIBUTABLE = {
    "20250901_warp",
    "20250405_amazon-q-developer-agent-20250405-dev",
}
LABELLED = [s for s in adapters.ADAPTERS if s not in NOT_ATTRIBUTABLE]


def fetch(key):
    path = os.path.join(CACHE, key.replace("/", "__"))
    if os.path.exists(path) and os.path.getsize(path):
        return open(path, "rb").read()
    raw = urllib.request.urlopen(BUCKET + urllib.parse.quote(key), timeout=300).read()
    open(path, "wb").write(raw)
    return raw


def resolved_set(submission):
    with urllib.request.urlopen(RESULTS.format(submission), timeout=60) as f:
        return set(json.load(f)["resolved"])


def candidates(trace_index):
    """§3: instances present in every submission, less the development sample."""
    common = set.intersection(*(set(m) for m in trace_index.values()))
    return sorted(common - set(DEV_INSTANCES))


def draw(instances, submission, stratum):
    """A fixed permutation. Taking the first k eligible from it is a uniform sample of
    the eligible set, which is what §3 asks for, without downloading the other 400."""
    order = sorted(instances)
    random.Random(f"{SEED}|{submission}|{stratum}").shuffle(order)
    return order


def readings(submission, raw):
    """Both readings of the <think> question (§5); identical for most submissions."""
    primary = adapters.extract(submission, raw, keep_think=False)
    alternative = adapters.extract(submission, raw, keep_think=True)
    return primary, alternative


def collect(submission, trace_index, resolved, pool, want):
    """Walk the permutation until `want` usable statements are found in each stratum."""
    found = {"resolved": [], "not_resolved": []}
    disposition = Counter()
    for stratum in ("not_resolved", "resolved"):
        wanted = [i for i in pool if (i in resolved) == (stratum == "resolved")]
        disposition[f"{stratum}_available"] = len(wanted)
        for instance in draw(wanted, submission, stratum):
            if len(found[stratum]) >= want:
                break
            key = trace_index[submission].get(instance)
            if not key:
                disposition[f"{stratum}_missing_trace"] += 1
                continue
            try:
                primary, alternative = readings(submission, fetch(key))
            except Exception as exc:                        # noqa: BLE001 - count, don't hide
                disposition[f"{stratum}_adapter_error:{type(exc).__name__}"] += 1
                continue
            if primary == adapters.SELECTION_UNCLEAR:
                disposition[f"{stratum}_selection_unclear"] += 1
                continue
            if primary == adapters.NO_REPORT:
                disposition[f"{stratum}_no_report"] += 1
                continue
            if len(primary) > MAX_STATEMENT:
                disposition[f"{stratum}_statement_unbounded"] += 1
                continue
            found[stratum].append((instance, primary, alternative))
            disposition[f"{stratum}_drawn"] += 1
    return found, disposition


def card_id(submission, instance, reading):
    seed = f"{SEED}|{submission}|{instance}|{reading}".encode()
    return "c" + hashlib.sha256(seed).hexdigest()[:12]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true",
                        help="plumbing check on the five excluded development instances")
    parser.add_argument("--run", action="store_true",
                        help="the real draw")
    args = parser.parse_args()
    if args.dev == args.run:
        parser.error("choose exactly one of --dev / --run")

    os.makedirs(CACHE, exist_ok=True)
    out = "cards-dev" if args.dev else "cards"
    os.makedirs(out, exist_ok=True)

    print("listing traces ...")
    with ThreadPoolExecutor(max_workers=10) as pool:
        listings = list(pool.map(trace_keys, adapters.ADAPTERS))
    trace_index = {
        s: {k.split("/")[-1].split(".")[0]: k for k in keys}
        for s, keys in zip(adapters.ADAPTERS, listings)
    }

    if args.dev:
        pool_ids, want = list(DEV_INSTANCES), 3
        print(f"development mode: {len(pool_ids)} excluded instances, "
              f"{want} per stratum, nothing here counts")
    else:
        pool_ids, want = candidates(trace_index), PER_STRATUM
        print(f"candidates common to all ten, less the development sample: {len(pool_ids)}")

    cards, key, dispositions = [], {}, {}
    for submission in LABELLED:
        resolved = resolved_set(submission)
        found, disposition = collect(submission, trace_index, resolved, pool_ids, want)
        for stratum, rows in found.items():
            for instance, primary, alternative in rows:
                for reading, text in (("primary", primary), ("keep_think", alternative)):
                    if reading == "keep_think" and alternative == primary:
                        continue          # nothing to label twice
                    if len(text) > MAX_STATEMENT:
                        # amendment 4. The primary reading is already filtered in
                        # collect(); this catches a second reading that only exceeds the
                        # bound once the deliberation is kept.
                        disposition[f"{stratum}_{reading}_statement_unbounded"] += 1
                        continue
                    cid = card_id(submission, instance, reading)
                    cards.append({"card_id": cid, "text": text})
                    key[cid] = {
                        "submission": submission,
                        "instance": instance,
                        "resolved": instance in resolved,
                        "reading": reading,
                    }
        dispositions[submission] = dict(disposition)
        drawn = sum(len(v) for v in found.values())
        print(f"  {submission:<50} {drawn:>3} statements  {dict(disposition)}")

    random.Random(f"{SEED}|shuffle").shuffle(cards)
    with open(os.path.join(out, "cards.jsonl"), "w", encoding="utf-8") as f:
        for card in cards:
            f.write(json.dumps(card, ensure_ascii=False) + "\n")

    # Labelling happens in sessions, not through the API (PREREGISTRATION.md §6), so
    # the deck is also written as batches small enough to paste into one. Batching is
    # presentation only: the shuffle above already fixed the order, and a card's batch
    # is therefore independent of anything about the card.
    #
    # A fixed card count is the wrong bound: statement length varies by three orders of
    # magnitude, so 80 cards is a comfortable session in one place and an impossible one
    # in another. Cut on whichever bound arrives first, walking the fixed order.
    batches, current, budget = [], [], 0
    for card in cards:
        if current and (len(current) >= BATCH_CARDS or budget + len(card["text"]) > BATCH_CHARS):
            batches.append(current)
            current, budget = [], 0
        current.append(card)
        budget += len(card["text"])
    if current:
        batches.append(current)
    for number, batch in enumerate(batches, start=1):
        path = os.path.join(out, f"batch-{number:02d}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for card in batch:
                f.write(json.dumps(card, ensure_ascii=False) + "\n")
    widest = max((sum(len(c["text"]) for c in b) for b in batches), default=0)
    print(f"{len(batches)} batches -> {out}/batch-NN.jsonl "
          f"(at most {BATCH_CARDS} cards / {BATCH_CHARS:,} chars; widest {widest:,})")
    json.dump(key, open(os.path.join(out, "key.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"seed": SEED, "per_stratum": want, "candidates": len(pool_ids),
               "not_attributable": sorted(NOT_ATTRIBUTABLE), "by_submission": dispositions},
              open(os.path.join(out, "disposition.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    leaked = {field for card in cards for field in card} - {"card_id", "text"}
    if leaked:
        raise SystemExit(f"cards carry fields they must not: {sorted(leaked)}")

    extra = sum(1 for v in key.values() if v["reading"] == "keep_think")
    print(f"\n{len(cards)} cards -> {out}/cards.jsonl "
          f"({len(cards) - extra} primary, {extra} second reading of <think>)")
    print(f"key withheld from the labeller -> {out}/key.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
