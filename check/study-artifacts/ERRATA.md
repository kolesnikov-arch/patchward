# Errata — Study #1 artifacts

Corrections applied to published artifacts after release, newest first. Each entry
records what changed, why, and the checksums either side of the change, so anyone
holding an earlier copy can tell exactly what is different.

---

## 2026-08-08 — third-party email addresses removed from three artifacts

**What was wrong.** Fifteen personal email addresses belonging to third parties were
present in published artifacts. They came from the text of public pull requests —
`Signed-off-by:` trailers and similar — and were carried into the artifacts verbatim
along with the rest of each PR's title and body.

Every one of these addresses is public at its source. That is not the point. In a
commit an address sits incidentally; in a downloadable dataset it sits collected, which
is the form address harvesters want and a different thing to publish. Nobody asked to
be included in this study, and the study does not need their addresses to work.

**What changed.**

Checksums below are of **the file as it arrives from a fresh clone** — LF line endings
for the `.jsonl` files, per `.gitattributes`. That is the only hash a reader can
reproduce, so it is the only one worth publishing.

| file | records touched | field | sha256 before → after |
|---|---|---|---|
| `review_sample.jsonl` | 5 of 120 | `body` | `1d497602…cd82024f` → `25868972…da8ed63b` |
| `review_pass2.jsonl` | 5 of 120 | `body` | `5a9dd3a3…fc18517c` → `6e4a72d0…f13696899` |
| `population.jsonl.gz` | 12 of 192 978 | `title` | `8f79cd01…6ac2d1bd` → `f1e6ff5a…b58e0f89` |

> **This table was wrong when first published, for one hour.** The first version carried
> checksums taken from a Windows working copy, where the `.jsonl` files sit in CRLF.
> `.gitattributes` stores them as LF, so no reader cloning this repository could have
> reproduced either figure — the same class of defect already recorded in the survey
> instrument's log, committed a second time by the same author in the document that
> documents it. Caught by cloning the repository and checking the hashes the way a
> stranger would, which is the only reason it was caught at all. The `.gz` figures were
> always correct: `.gitattributes` marks it `binary`, so no conversion applies.

Each address was replaced in place with the literal string `[email redacted]`. The
substitution was done on the raw line text rather than by re-serialising JSON, so every
byte outside the address itself is unchanged.

**What did not change.** Record counts are identical (120, 120, 192 978). No
`classification`, `note`, `review_id`, `url` or `_diff_ref` field was touched, so no
label moved and no drawn PR left or entered the sample. `RESULTS.md`, `summary.json`
and every figure derived from them are unaffected — the counts do not read the address
text. The scoring contract was not edited.

**Git history was deliberately not rewritten.** The addresses remain in earlier commits.
Rewriting history would rewrite `e7a2b6b`, `468fb76` and `508a191` — the commits that
froze the frame, the draw and the review sheet before any label existed. Those dated
hashes are the pre-registration; destroying them to remove addresses that are still
public at their source would trade the study's only real guarantee for a cosmetic gain,
and a silently rewritten history is indistinguishable from a tampered one. The trade is
not worth it, so the fix is applied forward and recorded here instead.

**Found by** an audit of the three public repositories, not by a complaint. Nobody on
that list has been in touch.
