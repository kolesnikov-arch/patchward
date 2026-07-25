"""Minimal GitHub REST client: stdlib only, rate-limit aware, resumable.

Written for a study that must be reproducible by a stranger, so it does three
things that a throwaway script wouldn't:

  * it never silently swallows a failure — a request that cannot be satisfied
    raises, and callers record the reason in a disposition row;
  * it respects both the documented rate limit and the undocumented secondary
    one, because a run that gets throttled halfway and quietly returns partial
    data would corrupt the sample without anyone noticing;
  * it caches raw responses to disk, so a run interrupted at hour three resumes
    instead of re-drawing.

Auth: see read_token(). Unauthenticated is 60 requests/hour and will not finish.
"""
import gzip
import hashlib
import json
import os
import pathlib
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
UA = "patchward-check-study/1.0 (+https://github.com/kolesnikov-arch/patchward)"

TOKEN_FILE_ENV = "GITHUB_TOKEN_FILE"
DEFAULT_TOKEN_FILE = "~/.patchward-study-token"


def read_token(explicit=None):
    """Resolve the token and say where it came from: (token, source).

    Order: explicit argument, $GITHUB_TOKEN, $GITHUB_TOKEN_FILE, then
    ~/.patchward-study-token.

    A file is here because this study runs over days: a session env var has to
    be retyped in every new terminal, and the run that gets skipped is the one
    that needs setting up first. The default path is deliberately *outside* the
    repository — a token inside a public working tree is one `git add -f` away
    from being published.
    """
    if explicit:
        return explicit.strip(), "argument"

    env = os.environ.get("GITHUB_TOKEN", "").strip()
    if env:
        return env, "$GITHUB_TOKEN"

    for raw_path, label in ((os.environ.get(TOKEN_FILE_ENV), f"${TOKEN_FILE_ENV}"),
                            (DEFAULT_TOKEN_FILE, DEFAULT_TOKEN_FILE)):
        if not raw_path:
            continue
        p = pathlib.Path(raw_path).expanduser()
        if not p.is_file():
            continue
        data = p.read_bytes()
        # Notepad and `Set-Content -Encoding utf8` on PowerShell 5 both prepend
        # a BOM; GitHub then answers 401 and the cause is invisible.
        if data.startswith(b"\xef\xbb\xbf"):
            data = data[3:]
        token = data.decode("utf-8", "replace").strip()
        if not token:
            continue
        _warn_if_inside_repo(p)
        return token, f"{label} ({p})"

    return "", "nowhere"


def _warn_if_inside_repo(path):
    try:
        cwd = pathlib.Path.cwd().resolve()
        if os.path.commonpath([path.resolve(), cwd]) == str(cwd):
            sys.stderr.write(
                f"gh: WARNING — token file {path} is inside the working tree. "
                f"Move it out; a secret in a repo eventually gets committed.\n")
    except ValueError:      # different drives on Windows
        pass


class RateLimited(RuntimeError):
    pass


class NotAvailable(RuntimeError):
    """The resource exists but cannot be retrieved (too large, 451, gone)."""


class Client:
    def __init__(self, token=None, cache_dir="cache/http", verbose=True):
        self.token, self.token_source = read_token(token)
        self.cache = pathlib.Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        self.requests_made = 0
        if not self.token:
            self._warn(f"no token found (looked in $GITHUB_TOKEN, "
                       f"${TOKEN_FILE_ENV}, {DEFAULT_TOKEN_FILE}) — "
                       f"60 req/hour, this will not finish")
        else:
            self._log(f"token from {self.token_source}")

    # -- plumbing ---------------------------------------------------------

    def _warn(self, msg):
        sys.stderr.write(f"gh: {msg}\n")

    def _log(self, msg):
        if self.verbose:
            sys.stderr.write(f"gh: {msg}\n")

    def _cache_path(self, url, accept):
        key = hashlib.sha256(f"{url}\n{accept}".encode()).hexdigest()[:32]
        return self.cache / f"{key}.gz"

    def _sleep_for_limit(self, headers):
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")
        if remaining is None or reset is None:
            return
        try:
            remaining, reset = int(remaining), int(reset)
        except ValueError:
            return
        if remaining > 2:
            return
        wait = max(0, reset - int(time.time())) + 2
        self._log(f"rate limit reached, sleeping {wait}s")
        time.sleep(wait)

    def get(self, path, accept="application/vnd.github+json", params=None,
            use_cache=True, max_retries=5):
        """GET a path or absolute URL. Returns (text, headers)."""
        url = path if path.startswith("http") else API + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)

        cp = self._cache_path(url, accept)
        if use_cache and cp.exists():
            with gzip.open(cp, "rt", encoding="utf-8") as f:
                return f.read(), {}

        headers = {"Accept": accept, "User-Agent": UA,
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        for attempt in range(max_retries):
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read().decode("utf-8", errors="replace")
                    self.requests_made += 1
                    self._sleep_for_limit(dict(r.headers))
                    with gzip.open(cp, "wt", encoding="utf-8") as f:
                        f.write(body)
                    return body, dict(r.headers)

            except urllib.error.HTTPError as e:
                hdrs = dict(e.headers or {})
                # 403/429 with a rate-limit signal: back off and retry.
                if e.code in (403, 429):
                    retry_after = hdrs.get("Retry-After")
                    if retry_after:
                        wait = int(retry_after) + 1
                    elif hdrs.get("X-RateLimit-Remaining") == "0":
                        wait = max(0, int(hdrs.get("X-RateLimit-Reset", 0))
                                   - int(time.time())) + 2
                    else:  # secondary limit, undocumented: exponential + jitter
                        wait = int((2 ** attempt) * 10
                                   + random.Random(attempt).random() * 5)
                    self._log(f"{e.code} on {url[:80]} — waiting {wait}s "
                              f"(attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                    continue
                if e.code in (404, 451, 410):
                    raise NotAvailable(f"{e.code} {url}") from e
                if e.code == 406:  # diff too large to render
                    raise NotAvailable(f"406 diff not renderable {url}") from e
                if 500 <= e.code < 600:
                    wait = 2 ** attempt
                    self._log(f"{e.code} server error — retrying in {wait}s")
                    time.sleep(wait)
                    continue
                raise

            except (urllib.error.URLError, TimeoutError, OSError) as e:
                wait = 2 ** attempt
                self._log(f"network error ({e}) — retrying in {wait}s")
                time.sleep(wait)

        raise RateLimited(f"gave up after {max_retries} attempts: {url}")

    def get_json(self, path, **kw):
        body, headers = self.get(path, **kw)
        return json.loads(body), headers

    # -- higher level -----------------------------------------------------

    def search_repos(self, query, per_page=100, pages=1):
        out = []
        for page in range(1, pages + 1):
            data, _ = self.get_json(
                "/search/repositories",
                params={"q": query, "sort": "stars", "order": "desc",
                        "per_page": per_page, "page": page})
            out += data.get("items", [])
            if len(data.get("items", [])) < per_page:
                break
            time.sleep(2)   # search API: 30 req/min
        return out

    def search_issues_count(self, query):
        """Cheap total_count for a search query (used for the ≥N PR filter)."""
        data, _ = self.get_json("/search/issues",
                                params={"q": query, "per_page": 1})
        time.sleep(2)
        return data.get("total_count", 0)

    def search_issues(self, query, per_page=100, max_items=1000):
        """Search issues/PRs. GitHub caps this at 1000 results per query."""
        out = []
        for page in range(1, (max_items // per_page) + 1):
            data, _ = self.get_json("/search/issues",
                                    params={"q": query, "per_page": per_page,
                                            "page": page, "sort": "created",
                                            "order": "asc"})
            items = data.get("items", [])
            out += items
            time.sleep(2)
            if len(items) < per_page:
                break
        return out

    def pull_diff(self, owner, repo, number):
        """Raw unified diff for a PR. Raises NotAvailable if unrenderable."""
        body, _ = self.get(f"/repos/{owner}/{repo}/pulls/{number}",
                           accept="application/vnd.github.v3.diff")
        return body
