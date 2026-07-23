# Writing an adapter

Your adapter is the only thing that knows how your agent works. fa-patchward
speaks to it through one tiny contract, once per task.

## The contract

- **stdin**: one JSON object — the task record. Always has `instance_id`. When
  `datasets` is installed it also carries `repo`, `base_commit`,
  `problem_statement`, `version`, and the benchmark's test fields.
- **stdout**: one JSON object — `{"instance_id": "<same id>", "model_patch": "<unified diff>"}`.
  Return an **empty** `model_patch` to abstain. Abstaining is honest and is never
  counted as a false-accept.
- **exit 0** on success. A non-zero exit, a timeout, or unparseable stdout is
  recorded as an abstain-with-error; the run continues.

Ungated by design: whatever diff you return is "shipped" as-is. That is the point
— fa-patchward measures what leaves when nothing checks it.

## Minimal example

`noop_agent.py` in this folder is a complete, working adapter that abstains on
every task. Copy it and replace `solve()`:

```python
def solve(task):
    # 1. check out task["repo"] at task["base_commit"]
    # 2. hand task["problem_statement"] to your agent
    # 3. return the unified diff it produces (git diff), or "" to abstain
    return my_agent.run(task)
```

## Wrapping an existing framework

If your agent already emits SWE-bench predictions (aider, SWE-agent, OpenHands,
your own harness), you do **not** need an adapter at all — skip `fa-patchward run`
and feed your existing `predictions.jsonl` straight into `fa-patchward report`. The adapter
path exists only for agents that don't already speak the predictions format.

## The one boundary

The task record only ever describes public-benchmark instances that ship their
own reference tests. There is no "point it at my private repo" mode — see
[`../WHERE_THIS_STOPS.md`](../WHERE_THIS_STOPS.md).
