# Contributing

Short version: **corrections are the most valuable thing you can send.** This is a
project about not fooling yourself, so a report that something here is wrong is a
contribution to the thesis, not an annoyance.

## The three things most worth sending

**1. A case `patchward check` gets wrong.** Either direction:

- *False positive* — it flagged a change that was perfectly legitimate (an
  intentional format change, an API rename, tightening a loose assertion).
- *False negative* — a change that rewrote its own evidence and slipped through.

Open an issue with the diff, or the smallest reproduction of it, and what you
expected. Real diffs beat descriptions. Every rule in
[`check/patchward/detect.py`](check/patchward/detect.py) is a claim about diff
structure, and each one can be wrong.

The current rules came from exactly this: the first version keyed on the word
`assert` and missed the sharpest real case in [RESULTS.md](RESULTS.md), because the
agent had rewritten the expected *values* instead. That miss was found by running
against real data. Yours may find the next one.

**2. A language or layout it doesn't recognise.** Test-file detection is a set of
path conventions, and it will not know about your monorepo. `--test-glob` is the
escape hatch; if you need it, that is a bug report — tell us the layout and it
should be built in.

**3. A hole in the evaluation.** [RESULTS.md](RESULTS.md) and
[PREREGISTRATION.md](PREREGISTRATION.md) are meant to be attacked. If a number
doesn't reconcile, if the scoring rules have a loophole, if a limitation is
understated — say so. Every figure recomputes from
[`evaluation-artifacts/`](evaluation-artifacts/) with a stdlib-only script; if your
recomputation disagrees with the published number, that is the highest-priority
issue this repository can receive.

## Pull requests

Welcome, for [`check/`](check/) (MIT). Please:

- Run `python check/tests/test_detect.py` — stdlib only, no install needed.
- Add a test for the case you're fixing. If it's a real-world diff, a fixture in
  `check/tests/fixtures/` is better than a synthetic one.
- Keep it dependency-free. `check` is pure stdlib on purpose: it has to run inside
  CI, offline, and air-gapped without a procurement conversation.

## What is not open to contribution

The tuned engine — the gates, the prompts, and the failure corpus behind
[RESULTS.md](RESULTS.md) — is not in this repository and is not accepting patches.
That boundary and its reasoning are written down in
[self-check/WHERE_THIS_STOPS.md](self-check/WHERE_THIS_STOPS.md).

## Reporting something sensitive

If you find a way to make `patchward check` report *clean* on a change that clearly
rewrote its own tests, and you'd rather not post it publicly, mail
[kolesnikov.arch@gmail.com](mailto:kolesnikov.arch@gmail.com) first. It will be
credited when fixed unless you'd rather not be.

## Credit

Anyone whose report changes a rule gets named in the commit and in the release
notes. If a validation run of yours produces a number, it gets cited with your name
on it — that is how a measurement earns trust it didn't have.
