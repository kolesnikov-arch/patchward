"""`fa-patchward init` — scaffold a working directory after a bare `pip install`.

So a stranger who ran `pip install fa-patchward` (no repo clone) can get to a
runnable state in one command: it drops an adapter stub and a pre-registration
file into the current directory, then prints the four steps.
"""
import os

ADAPTER_TEMPLATE = '''#!/usr/bin/env python3
"""Your adapter: teach fa-patchward how to call your agent.

Contract (one task per invocation):
  stdin  -> {"instance_id", "repo", "base_commit", "problem_statement", ...}
  stdout <- {"instance_id": "<same id>", "model_patch": "<unified diff, or empty>"}

Return an empty model_patch to abstain (honest, never counted as a false-accept).
This stub abstains on everything; replace solve() with a call into your agent.
"""
import json
import sys


def solve(task):
    # task always has "instance_id"; with `datasets` installed it also has
    # "repo", "base_commit", "problem_statement", and the benchmark test fields.
    #
    # TODO: check out task["repo"] at task["base_commit"], hand your agent
    # task["problem_statement"], and return the unified diff it produces
    # (e.g. `git diff`). Return "" to abstain.
    return ""


def main():
    task = json.load(sys.stdin)
    patch = solve(task)
    json.dump({"instance_id": task["instance_id"], "model_patch": patch},
              sys.stdout)
    sys.stdout.write("\\n")


if __name__ == "__main__":
    main()
'''

PREREG_TEMPLATE = """# Pre-registration — fill in BEFORE you look at any number

A self-measurement only means something if you committed to it before seeing the
result. Fill this in and commit it before running. Changing it after seeing your
number means you are tuning, not measuring.

## 1. Agent
- Framework + version / model + settings:
- How it decides it is "done":

## 2. Task set (frozen)
- Dataset / split: SWE-bench/SWE-bench_Lite / test
- N / seed / exclusions:
- frozen/selection.json committed at git SHA:

## 3. Run policy (set now)
- Per-task timeout:
- Re-run rule for crashes/timeouts (never re-roll a completed outcome):

## 4. Prediction (write your guess first)
- I expect roughly ___ / ___  ( ___ % ) silent false-accepts.

After the run, `fa-patchward verify` must pass against these frozen files.
"""

_FILES = {"my_agent.py": ADAPTER_TEMPLATE, "PREREGISTRATION.md": PREREG_TEMPLATE}


def init(target_dir="."):
    written, skipped = [], []
    for name, content in _FILES.items():
        path = os.path.join(target_dir, name)
        if os.path.exists(path):
            skipped.append(name)
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(name)

    if written:
        print("scaffolded:", ", ".join(written))
    if skipped:
        print("kept existing (not overwritten):", ", ".join(skipped))
    print("\nNext:")
    print("  1. Fill in PREREGISTRATION.md and commit it (freeze before you look).")
    print("  2. fa-patchward select --dataset SWE-bench/SWE-bench_Lite --n 50 --seed 50")
    print("  3. edit my_agent.py to call your agent")
    print("  4. fa-patchward run --agent 'python my_agent.py' --label my-agent")
    print("     ...evaluate predictions.jsonl with the public swebench harness...")
    print("  5. fa-patchward report --reports logs/run_evaluation/<run_id>")
