#!/usr/bin/env python3
"""Reference adapter: the honest do-nothing agent.

It reads one task record (JSON) from stdin and prints one result (JSON) to
stdout with an empty patch — i.e. it abstains on every task. Useful to (a) smoke-
test fa-patchward end-to-end without a real agent or Docker, and (b) show the exact
contract your own adapter must satisfy.

A real adapter replaces `solve()` with a call into your agent, returning a
unified-diff string for the repo at base_commit. Return "" to abstain.
"""
import json
import sys


def solve(task):
    # task has at least {"instance_id": ...} and, when `datasets` is installed,
    # {"repo", "base_commit", "problem_statement", ...}. Do your work here.
    return ""  # abstain


def main():
    task = json.load(sys.stdin)
    patch = solve(task)
    json.dump({"instance_id": task["instance_id"], "model_patch": patch},
              sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
