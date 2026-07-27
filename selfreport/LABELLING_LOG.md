# Labelling log — what actually happened, 2026-07-27

The contract fixes the rules; this file records the execution against them, including the
parts that went wrong. It is written from the session transcripts, not from memory, and it
ships with the results (PREREGISTRATION.md §7.8).

## Judges

| Pass | Model | Harness |
|---|---|---|
| 1 | `claude-opus-5` | Claude Code |
| 2 | `deepseek-v4-pro` (launcher label `deepseek-v4-pro[1m]`, effort max) | Claude Code driven through a local Anthropic-compatible proxy to `api.deepseek.com` |

Per-batch model and session id: `cards/labels/judges.json`.

Amendment 3 named `deepseek-v4-pro-202606`. The build that actually ran reports itself as
`deepseek-v4-pro`; recorded as observed rather than as written in advance.

## One batch, one session — verified

Each labelling session read exactly one batch file and produced exactly one label file:
15 sessions in pass 1, 15 in pass 2. No session saw a sibling batch or another run's labels.

This was checked rather than assumed: the launcher for pass 2 runs `claude --continue`, which
resumes a conversation and would have chained the batches together. It did not — every batch
forked its own session id, and the transcripts show one `batch-NN.jsonl` read per session.

## The key never entered a session

`key.json` — the file holding each card's resolved/not-resolved status — appears in the
transcripts only as a filename inside directory listings. Its content never does: the string
`"resolved"` occurs **zero** times across every session of both passes, and it would occur
1190 times in any session that had read the file. Card-level blinding held.

## What did leak: the stratification, in six sessions

Six sessions opened `cards/disposition.json`, which states per submission
`not_resolved_drawn: 60` and `resolved_drawn: 60`. That is not card-level status, but it is
exactly what the labelling prompt forbids handing a judge — *"any statement about how many
cards came from solved versus failed tasks"* — because a judge who knows half the deck comes
from failures may hedge differently.

| Pass | Batches | Sessions |
|---|---|---|
| 1 | 01, 03, 04, 06, 08 | `b2739ab2`, `5bc4b71b`, `4d62279d`, `26bcbc47`, `4f20b231` |
| 2 | 05 | `a30b2427` |

**Those six runs were moved to `cards/labels/discarded/` and the batches re-run in fresh
sessions.** They are kept, not deleted, so the fact that they happened is auditable.

A seventh run was discarded for an unrelated defect: the first pass-2 run of batch 09
(`fec59e74`) emitted one card twice and dropped the batch's last card. The deck contains no
duplicate ids — all 1190 are distinct — so the duplication was the session's, not the data's.
Per the labelling prompt, a short or malformed run is re-run whole rather than patched.

## Re-runs, round 2 (same day, 13:2x–13:3x)

The five pass-1 batches were re-run and are clean: each session read only its own batch, and
neither the key nor the stratification appears in any of the five transcripts. Those runs are
live.

The pass-2 re-run of batch 05 was discarded as well, for a defect rather than a leak: it
labelled a card id that does not exist in the deck — `c76c90476ecbb`, a garbled copy of
`c76c90476bbec` — and left the real card, position 51 of the batch, unlabelled. Recovering it
would mean deciding by hand which card a mistyped id referred to, which is the kind of patching
the labelling prompt rules out. Re-run whole instead.

At the time of writing, pass 2 is missing live runs for batches 05 and 09.

## Why it happened, and what changed

The sessions were pointed at `cards/` — the directory that also holds `key.json`,
`disposition.json` and every other batch — instead of at the prepared per-batch directory
holding only the prompt and one batch. They were also not told their pass number, so pass-2
sessions wrote files named `pass1-…`; those were refiled by session identity, which the
transcripts establish unambiguously (one batch read, one file written, per session).

Fix, applied before the re-runs: every session runs **from its own
`cards/labels/pass<N>-batch-<NN>/` directory**, which contains exactly two files, and is told
its pass number in the first line. Nothing else is reachable from there.

## What this does not excuse

The blinding rule existed in writing before the labelling began, and it was broken in six
sessions anyway. It was caught by auditing the transcripts afterwards rather than by the
setup preventing it — the setup existed and was bypassed by pointing the sessions at the
wrong directory. The re-runs remove the contaminated labels from the numbers; they do not
remove the fact that a study about self-reported correctness had to check its own execution
after the fact to find out what its judges had seen.
