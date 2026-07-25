"""Study #1 runner — one subcommand per stage of the pre-registered contract.

    python -m study auth       check the token works before anything else
    python -m study frame      build + freeze the repository frame     (§3)
    python -m study enumerate  list every merged PR in the window      (§3)
    python -m study draw       seeded, stratified draw of 3000         (§3)
    python -m study fetch      download the drawn diffs (resumable)    (§3)
    python -m study score      run the pinned instrument over them     (§2)
    python -m study report     emit RESULTS + summary.json             (§5)
    python -m study review     export the blind review sample          (§4)
    python -m study secondpass blank copy of it for a 2nd blind pass   (§4)
    python -m study tally      fold the filled-in review into numbers  (§4)
    python -m study verify     recompute everything from raw           (§5.8)

The stages are separate commands, not one script, because the contract freezes
the frame and the draw *before* any verdict exists. A single `run()` would make
it possible — and therefore eventually tempting — to redraw after seeing a
number.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time
import urllib.error

from . import collect, frame as frame_mod, gh, report as report_mod, sample as sample_mod
from .gh import Client

ART = pathlib.Path("study-artifacts")


def _instrument_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True,
                             cwd=pathlib.Path(__file__).resolve().parents[1])
        dirty = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True,
                               cwd=pathlib.Path(__file__).resolve().parents[1])
        sha = out.stdout.strip() or "UNKNOWN"
        return sha + ("-dirty" if dirty.stdout.strip() else "")
    except Exception:
        return "UNKNOWN"


def _load_frame():
    return json.loads((ART / "frame.json").read_text(encoding="utf-8"))


def _population():
    """Gzipped by default; an existing uncompressed file is still honoured."""
    gz, plain = ART / "population.jsonl.gz", ART / "population.jsonl"
    return plain if (plain.exists() and not gz.exists()) else gz


def cmd_auth(a):
    """Is a token visible, does GitHub accept it, and what is the budget?

    Its own command because the alternative is finding out at hour three of
    `enumerate`, and because "the token is set" and "the token works" are
    different claims — a BOM or a trailing space satisfies the first and fails
    the second.
    """
    token, source = gh.read_token()
    if not token:
        print("no token found. Looked, in order:")
        print("  $GITHUB_TOKEN")
        print(f"  ${gh.TOKEN_FILE_ENV}")
        print(f"  {gh.DEFAULT_TOKEN_FILE}")
        print("\nUnauthenticated is 60 requests/hour; the study needs thousands.")
        return 1

    shape = (token.split("_")[0] + "_…") if "_" in token else "…"
    print(f"token    {shape} ({len(token)} chars) from {source}")

    client = Client(token=token, verbose=False)
    try:
        who, headers = client.get_json("/user", use_cache=False)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("\nGitHub rejected it: 401 Bad credentials.")
            print("Usual causes: expired token, a stray space or newline in the")
            print("value, or the file saved with a BOM.")
            return 1
        raise

    print(f"account  {who.get('login')}")
    scopes = headers.get("X-OAuth-Scopes")
    if scopes is not None:
        print(f"scopes   {scopes or '(none — fine, public repositories only)'}")

    limits, _ = client.get_json("/rate_limit", use_cache=False)
    resources = limits.get("resources", {})
    for name in ("core", "search"):
        r = resources.get(name)
        if r:
            reset = time.strftime("%H:%M:%S", time.localtime(r["reset"]))
            print(f"{name:9}{r['remaining']}/{r['limit']} left, resets {reset}")

    if resources.get("core", {}).get("limit", 0) < 1000:
        print("\nThat is an unauthenticated budget — the token is not in effect.")
        return 1

    print("\nOK. Next: python -m study frame --per-group 1")
    return 0


def cmd_frame(a):
    f = frame_mod.build(Client(), ART / "frame.json", per_group=a.per_group)
    if f.get("smoke"):
        print("\n  *** SMOKE FRAME — marked smoke:true in frame.json.")
        print("      Numbers from this run are for checking the plumbing only.")
        print("      Delete study-artifacts/ and cache/ before the real run.")
    return 0


def cmd_enumerate(a):
    sample_mod.enumerate_prs(Client(), _load_frame(), _population())
    return 0


def cmd_draw(a):
    sample_mod.draw(_population(), ART / "sample.json",
                    target_n=a.n, seed=a.seed)
    return 0


def cmd_fetch(a):
    collect.fetch(Client(), ART / "sample.json")
    return 0


def cmd_score(a):
    commit = _instrument_commit()
    if commit.endswith("-dirty") and not a.allow_dirty:
        sys.stderr.write(
            "study: the working tree is dirty, so the instrument is not pinned.\n"
            "       Contract §2 requires a pinned commit. Commit first, or pass\n"
            "       --allow-dirty for a throwaway run whose numbers you discard.\n")
        return 2
    collect.score(ART / "sample.json", ART / "results.jsonl")
    return 0


def cmd_report(a):
    rows = report_mod.load(ART / "results.jsonl")
    summary = report_mod.summarize(rows)

    review = None
    rp, kp = ART / "review_sample.jsonl", ART / "review_key.json"
    if rp.exists() and kp.exists():
        review = report_mod.score_review(rp, kp)
        if not review["reviewed"]:
            review = None

    summary["instrument_commit"] = _instrument_commit()
    summary["review"] = review

    # Second-pass agreement, if a second pass exists (contract §4).
    second = sorted(ART.glob("review_pass*.jsonl"))
    summary["pass_agreement"] = (
        report_mod.pass_agreement(rp, second[0]) if rp.exists() and second else None)
    (ART / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (ART / "RESULTS.md").write_text(
        report_mod.render(summary, review, summary["instrument_commit"]),
        encoding="utf-8")

    print(f"report -> {ART / 'RESULTS.md'}, {ART / 'summary.json'}")
    n, k = summary["analysed"], summary["high_severity"]
    lo, hi = summary["ci95_clopper_pearson"]
    print(f"  {k}/{n} flagged high severity "
          f"({100.0 * k / n:.1f}%) CI [{lo * 100:.1f}%, {hi * 100:.1f}%]"
          if n else "  nothing analysed")
    if review is None:
        print("  blind review NOT done — the headline means little without it (§4)")
    else:
        # The precision is the number most likely to be unflattering (contract
        # §1), so it prints next to the headline rather than only in the file.
        lo, hi = (review.get("precision_ci95") or ["?", "?"])[:2] \
            if isinstance(review.get("precision_ci95"), list) \
            else (review.get("precision_ci95"), None)
        p = review.get("precision")
        print(f"  blind review: {review['reviewed']} reviewed · "
              f"precision {p:.1%} {lo if hi is None else f'[{lo}, {hi}]'} · "
              f"{review.get('false_positive', 0)} false positive, "
              f"{review.get('missed_by_tool', 0)} missed, "
              f"{review.get('undecidable', 0)} undecidable")
    return 0


def cmd_review(a):
    # A client is passed so the PR descriptions come down with the sample:
    # rubric category 2 turns on whether the PR *states* an intentional change,
    # so the reviewer needs the description, and needs it offline.
    client = None if a.no_bodies else Client()
    report_mod.export_review_sample(report_mod.load(ART / "results.jsonl"),
                                    ART / "review_sample.jsonl", client=client)
    return 0


def cmd_serve(a):
    from .review_ui import serve
    serve(port=a.port, open_browser=not a.no_browser, sheet=a.sheet)
    return 0


def cmd_secondpass(a):
    """A blank copy of the sheet for an independent second pass (contract §4).

    Blank, not a continuation: a second pass that can see the first one's labels
    measures nothing. Reliability comes from the two passes not knowing about
    each other.
    """
    src = ART / "review_sample.jsonl"
    dst = ART / f"review_pass{a.n}.jsonl"
    if not src.exists():
        sys.stderr.write(f"no {src} — run `python -m study review` first\n")
        return 2
    if dst.exists() and not a.force:
        sys.stderr.write(f"{dst} already exists — a pass may be in progress. "
                         f"--force resets it, discarding its answers.\n")
        return 2

    rows = [json.loads(l) for l in src.open(encoding="utf-8") if l.strip()]
    with dst.open("w", encoding="utf-8") as f:
        for r in rows:
            blank = {**r, "classification": "", "note": ""}
            blank.pop("answered_at", None)
            f.write(json.dumps(blank, ensure_ascii=False) + "\n")

    print(f"pass {a.n}: {len(rows)} cards, labels blank -> {dst}")
    print(f"  classify it with: python -m study serve --sheet {dst}")
    print(f"  then `report` folds the agreement between passes in automatically")
    return 0


def cmd_tally(a):
    r = report_mod.score_review(ART / "review_sample.jsonl",
                                ART / "review_key.json")
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0


def cmd_verify(a):
    """Recompute the published summary from raw rows; fail loudly on drift."""
    rows = report_mod.load(ART / "results.jsonl")
    fresh = report_mod.summarize(rows)
    published = json.loads((ART / "summary.json").read_text(encoding="utf-8"))

    problems = []
    for key in ("drawn", "analysed", "excluded", "high_severity",
                "by_finding_kind", "by_language_group", "by_diff_size",
                "verdicts", "excluded_reasons"):
        if fresh[key] != published.get(key):
            problems.append(f"{key}: recomputed {fresh[key]!r} != "
                            f"published {published.get(key)!r}")

    for key in ("rate", "ci95_clopper_pearson"):
        a_, b_ = fresh[key], published.get(key)
        if isinstance(a_, list):
            if not b_ or any(abs(x - y) > 1e-9 for x, y in zip(a_, b_)):
                problems.append(f"{key}: {a_} != {b_}")
        elif a_ is not None and b_ is not None and abs(a_ - b_) > 1e-12:
            problems.append(f"{key}: {a_} != {b_}")

    # The disposition table must account for every drawn PR (contract §5.2).
    if fresh["analysed"] + fresh["excluded"] != fresh["drawn"]:
        problems.append(f"disposition does not sum: "
                        f"{fresh['analysed']} + {fresh['excluded']} "
                        f"!= {fresh['drawn']}")

    if problems:
        print("VERIFY FAILED")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"verify OK — {fresh['analysed']} analysed, "
          f"{fresh['high_severity']} flagged, disposition sums to "
          f"{fresh['drawn']}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="study", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in [("auth", cmd_auth), ("enumerate", cmd_enumerate),
                     ("fetch", cmd_fetch), ("report", cmd_report),
                     ("tally", cmd_tally), ("verify", cmd_verify)]:
        sub.add_parser(name).set_defaults(func=fn)

    fr = sub.add_parser("frame", help="build + freeze the repository frame")
    fr.add_argument("--per-group", type=int, default=None, metavar="N",
                    help="repositories per language group; anything other than "
                         "the contract's 50 marks the frame as a smoke run")
    fr.set_defaults(func=cmd_frame)

    rv = sub.add_parser("review", help="export the blind review sheet")
    rv.add_argument("--no-bodies", action="store_true",
                    help="skip fetching PR descriptions (offline)")
    rv.set_defaults(func=cmd_review)

    sv = sub.add_parser("serve", help="review the sheet in a local browser UI")
    sv.add_argument("--port", type=int, default=8731)
    sv.add_argument("--no-browser", action="store_true")
    sv.add_argument("--sheet", metavar="PATH", default=None,
                    help="sheet to classify (default: the primary review sheet; "
                         "point it at a pass file for the second pass)")
    sv.set_defaults(func=cmd_serve)

    sp = sub.add_parser("secondpass",
                        help="blank copy of the sheet for an independent 2nd pass")
    sp.add_argument("-n", type=int, default=2, help="pass number (default 2)")
    sp.add_argument("--force", action="store_true",
                    help="overwrite an existing pass file, discarding its answers")
    sp.set_defaults(func=cmd_secondpass)

    d = sub.add_parser("draw")
    d.add_argument("--n", type=int, default=sample_mod.TARGET_N)
    d.add_argument("--seed", type=int, default=sample_mod.SEED)
    d.set_defaults(func=cmd_draw)

    s = sub.add_parser("score")
    s.add_argument("--allow-dirty", action="store_true")
    s.set_defaults(func=cmd_score)

    a = p.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
