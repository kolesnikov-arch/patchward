# Development sample — frozen before the study runs

**Date-stamped: 2026-07-26 (see this file's git history).**

This study reads agent reasoning traces in ten different container formats. Writing the code
that extracts "the agent's final message" from each format requires **looking at traces** — and
looking at traces is looking at the data. If the extractor were tuned on the same instances the
study later scores, the instrument would be fitted to the outcome.

So the extractors are built on a small sample that is **named here before the study runs and
excluded from every reported number.**

## The sample

Five instances, one per repository, chosen deterministically: of the 488 instance ids present in
all ten submissions, group by repository, sort, take the alphabetically first id from each of the
first five repositories.

| # | instance |
|---|---|
| 1 | `astropy__astropy-12907` |
| 2 | `django__django-10097` |
| 3 | `matplotlib__matplotlib-13989` |
| 4 | `mwaskom__seaborn-3069` |
| 5 | `pallets__flask-5014` |

**These five are excluded from the study for every submission.** Reported denominators are
therefore 483 candidate instances, not 488, before any further filtering the pre-registration
specifies.

## The submissions in scope

Ten, selected to cover every container format observed, and listed before collection:

| submission | trace files |
|---|---:|
| `20251127_openhands_claude-opus-4-5` | 489 |
| `20250522_tools_claude-4-opus` | 500 |
| `20250902_atlassian-rovo-dev` | 500 |
| `20250901_warp` | 500 |
| `20250715_qodo_command` | 500 |
| `20250930_zai_glm4-6` | 499 |
| `20251205_sonar-foundation-agent_claude-opus-4-5` | 500 |
| `20250928_trae_doubao_seed_code` | 500 |
| `20250405_amazon-q-developer-agent-20250405-dev` | 500 |
| `20251215_livesweagent_claude-opus-4-5` | 500 |

Instances common to all ten: **488**. Adding or dropping a submission after this file is
committed is permitted only as an explicit, dated amendment stating the reason — never silently.

## Where the data comes from

Traces are **not** in the `SWE-bench/experiments` git repository. Each submission's
`metadata.yaml` points outward:

```
assets:
  logs:  s3://swe-bench-submissions/verified/<submission>/logs
  trajs: s3://swe-bench-submissions/verified/<submission>/trajs
```

The bucket is readable over plain HTTPS with a prefix and no credentials:

```bash
curl "https://swe-bench-submissions.s3.amazonaws.com/?list-type=2&prefix=verified/<submission>/trajs/&max-keys=10"
```

Resolution status comes from the same repository's published evaluation:
`evaluation/verified/<submission>/results/results.json`, keys `resolved` and `no_generation`.

## What this file does not fix

The scoring rubric, the sampling of instances to be labelled, the labelling protocol and the
reporting commitments are **not** settled here. They belong in `PREREGISTRATION.md`, which is
committed before collection and after the extractors are frozen — because the rubric has to be
able to name what the extractors return.
