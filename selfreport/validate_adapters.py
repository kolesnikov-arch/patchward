"""Check every adapter against the frozen development sample.

Downloads the five instances named in DEV_SAMPLE.md for all ten submissions and prints
what each adapter extracted, so the extraction can be inspected rather than trusted.
Standard library only; needs network. Caches under ./dev-cache.

    python validate_adapters.py

An adapter is behaving when it returns a paragraph the agent actually wrote, or one of
the two explicit markers. Empty output, or output the length of a whole trace, means the
container changed and the adapter has to be looked at again.
"""

import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import adapters

def utf8_stdout():
    """Windows consoles default to a codepage that dies on the first non-ASCII trace.
    Guarded, because wrapping an already-wrapped stdout closes the buffer underneath it."""
    if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )


utf8_stdout()

BUCKET = "https://swe-bench-submissions.s3.amazonaws.com/"
CACHE = "dev-cache"

DEV_INSTANCES = [
    "astropy__astropy-12907",
    "django__django-10097",
    "matplotlib__matplotlib-13989",
    "mwaskom__seaborn-3069",
    "pallets__flask-5014",
]


def trace_keys(submission):
    """List every trace object for a submission. The bucket needs a prefix; the root is closed."""
    keys, token = [], None
    while True:
        query = {
            "list-type": "2",
            "prefix": f"verified/{submission}/trajs/",
            "max-keys": "1000",
        }
        if token:
            query["continuation-token"] = token
        body = urllib.request.urlopen(
            BUCKET + "?" + urllib.parse.urlencode(query), timeout=60
        ).read().decode()
        keys += re.findall(r"<Key>(.*?)</Key>", body)
        token = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", body)
        if not (token and "<IsTruncated>true" in body):
            return keys
        token = token.group(1)


def fetch(key):
    path = os.path.join(CACHE, key.replace("/", "__"))
    if os.path.exists(path) and os.path.getsize(path):
        return open(path, "rb").read()
    raw = urllib.request.urlopen(BUCKET + urllib.parse.quote(key), timeout=300).read()
    open(path, "wb").write(raw)
    return raw


def main():
    os.makedirs(CACHE, exist_ok=True)
    print(f"{'submission':<50} {'instance':<28} {'chars':>7}  extracted")
    print("-" * 150)
    problems = 0
    for submission in adapters.ADAPTERS:
        by_instance = {k.split("/")[-1].split(".")[0]: k for k in trace_keys(submission)}
        wanted = [by_instance[i] for i in DEV_INSTANCES if i in by_instance]
        with ThreadPoolExecutor(max_workers=5) as pool:
            traces = list(pool.map(fetch, wanted))
        for key, raw in zip(wanted, traces):
            instance = key.split("/")[-1].split(".")[0]
            try:
                out = adapters.extract(submission, raw)
            except Exception as exc:                       # noqa: BLE001 - report, don't hide
                print(f"{submission:<50} {instance:<28}   RAISED {type(exc).__name__}: {exc}")
                problems += 1
                continue
            note = ""
            if out == adapters.SELECTION_UNCLEAR:
                note = "  [several candidates; the submitted one is not identifiable]"
            elif out == adapters.NO_REPORT:
                note = "  [nothing was stated outside deliberation]"
            elif not out.strip():
                note, problems = "  ** EMPTY **", problems + 1
            elif len(out) > 20000:
                note, problems = "  ** IMPLAUSIBLY LONG **", problems + 1
            preview = re.sub(r"\s+", " ", out)[:70]
            print(f"{submission:<50} {instance:<28} {len(out):>7}  {preview}{note}")
    print(f"\nproblems: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
