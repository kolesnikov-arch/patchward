"""patchward — does this change edit the tests that judge it?

A flag, not a gate. Reads a diff; runs nothing; blocks nothing.
"""
from .detect import Finding, Result, analyse

__version__ = "0.1.0"
__all__ = ["analyse", "Result", "Finding", "__version__"]
