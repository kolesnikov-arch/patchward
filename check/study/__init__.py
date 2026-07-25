"""Study #1 — the base rate of self-graded changes in public pull requests.

Run against the pre-registered contract in ../PREREGISTRATION_PR_STUDY.md,
which was committed before any data was collected. Not part of the installable
`patchward-check` package: this is the research harness, and it ships in the
repository so the study can be reproduced, not on PyPI.
"""
__all__ = ["gh", "frame", "sample", "collect", "report", "stats"]
