"""Local blind-review tool — `python -m study serve`.

The review in contract §4 is 120 diffs classified one at a time, and it is the
part of the study most likely to fail. Not because it is hard, but because doing
it over 120 JSON lines in an editor gets careless around item forty, and a
careless review produces a precision number that means nothing while looking
exactly like one that does.

So: one screen per case, the diff already on it, six keys, saved after every
answer, resumable, and undoable. The reviewer never opens GitHub and never sees
the instrument's verdict — `review_key.json` is not read by this server at all.

`--sheet` exists for the second independent pass (§4): the same 120 cards with
the labels blanked, so the second pass cannot see the first one's answers.

stdlib only. Binds to localhost. Nothing leaves the machine.
"""
import html
import http.server
import json
import pathlib
import socketserver
import time
import webbrowser

ART = pathlib.Path("study-artifacts")
CACHE = pathlib.Path("cache/diffs")
SHEET = ART / "review_sample.jsonl"

RUBRIC = [
    ("1", "Retracted evidence",
     "An expectation that previously held was changed or removed, and the PR "
     "gives no stated reason for it."),
    ("2", "Justified expectation change",
     "Same structural change, but the PR states an intentional "
     "behaviour / format / API change that requires it."),
    ("3", "Nothing retracted",
     "Tests changed — new coverage, or mechanical scaffolding (a mock stub, a "
     "moved import) — but no existing expectation was removed or altered."),
    ("4", "Unrelated test change",
     "Test edit not connected to the source change — lint, rename, flake fix, "
     "infrastructure."),
    ("5", "Undecidable from the diff alone",
     "Counted separately. Never resolved in the instrument's favour."),
    ("6", "No test change in this pull request",
     "The diff touches no test file at all. Counted separately — it is not "
     "'nothing retracted', and it is not undecidable."),
]


def _load():
    with SHEET.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _save(rows):
    tmp = SHEET.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(SHEET)


def _last_answered(rows):
    """The answer to undo: latest by timestamp, ties broken by sheet order.

    Rows answered before timestamps existed (or filled in outside this server)
    carry no `answered_at`, and without the index tiebreak they all compare
    equal — `max` would then return the *first* of them, i.e. undo would walk
    backwards from the top of the sheet instead of from where the reviewer is.
    """
    answered = [(r.get("answered_at") or 0, i, r)
                for i, r in enumerate(rows)
                if str(r.get("classification", "")).strip()]
    if not answered:
        return None
    return max(answered)[2]


def _undo_link(rows):
    last = _last_answered(rows)
    if not last:
        return ""
    return (f'<a href="/undo">&#8630; undo {last["review_id"]}</a>')


def _diff_for(row):
    p = CACHE / row.get("_diff_ref", "")
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace")
    return "[diff not in cache — run `python -m study fetch` first]"


def _render_diff(text, limit=1200):
    lines = text.splitlines()
    truncated = len(lines) > limit
    out = []
    for ln in lines[:limit]:
        cls = ""
        if ln.startswith("+++") or ln.startswith("---"):
            cls = "meta"
        elif ln.startswith("@@"):
            cls = "hunk"
        elif ln.startswith("diff --git"):
            cls = "file"
        elif ln.startswith("+"):
            cls = "add"
        elif ln.startswith("-"):
            cls = "del"
        out.append(f'<span class="{cls}">{html.escape(ln) or "&nbsp;"}</span>')
    if truncated:
        out.append(f'<span class="meta">… {len(lines) - limit} more lines '
                   f'(full diff in cache)</span>')
    return "\n".join(out)


PAGE = """<!doctype html><meta charset="utf-8">
<title>blind review — {done}/{total}</title>
<style>
 :root {{ color-scheme: light dark; }}
 body {{ font: 14px/1.5 ui-sans-serif, system-ui, sans-serif; margin: 0;
        background: #0d1117; color: #c9d1d9; }}
 header {{ position: sticky; top: 0; background: #161b22; padding: 10px 18px;
          border-bottom: 1px solid #30363d; display: flex; gap: 18px;
          align-items: baseline; z-index: 5; }}
 .bar {{ flex: 1; height: 6px; background: #30363d; border-radius: 3px; }}
 .bar > i {{ display: block; height: 100%; background: #3fb950; border-radius: 3px;
            width: {pct}%; }}
 main {{ padding: 18px; max-width: 1100px; }}
 h1 {{ font-size: 16px; margin: 0 0 4px; }}
 .sub {{ color: #8b949e; font-size: 12px; margin-bottom: 14px; }}
 .body {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px;
         padding: 12px; margin-bottom: 14px; white-space: pre-wrap;
         max-height: 220px; overflow: auto; }}
 pre {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px;
       padding: 12px; overflow: auto; max-height: 52vh; font-size: 12px;
       line-height: 1.45; }}
 pre span {{ display: block; }}
 .add {{ color: #3fb950; }} .del {{ color: #f85149; }}
 .hunk {{ color: #58a6ff; }} .file {{ color: #d2a8ff; font-weight: 600; }}
 .meta {{ color: #8b949e; }}
 form {{ position: sticky; bottom: 0; background: #161b22; padding: 12px 18px;
        border-top: 1px solid #30363d; }}
 button {{ display: block; width: 100%; text-align: left; margin: 4px 0;
          background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
          border-radius: 6px; padding: 8px 12px; font: inherit; cursor: pointer; }}
 button:hover {{ border-color: #58a6ff; }}
 kbd {{ background: #30363d; border-radius: 3px; padding: 1px 6px;
       margin-right: 8px; font-family: ui-monospace, monospace; }}
 button i {{ color: #8b949e; font-style: normal; font-size: 12px; }}
 input[name=note] {{ width: 100%; margin-top: 8px; padding: 7px 10px;
   background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
   color: inherit; font: inherit; }}
 a {{ color: #58a6ff; }}
</style>
<header>
  <b>{done}/{total}</b><div class="bar"><i></i></div>
  <span class="meta">{rid}</span>
  {undo}
</header>
<main>
  <h1>{title}</h1>
  <div class="sub">{changed_lines} changed lines · classify from the diff and
    the description below · <a href="{url}" target="_blank" rel="noopener">open on
    GitHub</a> only if you must</div>
  {body_block}
  <pre>{diff}</pre>
</main>
<form method="post" action="/answer">
  <input type="hidden" name="rid" value="{rid}">
  {buttons}
  <input name="note" placeholder="note (optional)" autocomplete="off">
</form>
<script>
 document.addEventListener('keydown', e => {{
   if (e.target.tagName === 'INPUT' && e.key !== 'Enter') return;
   const b = document.querySelector('button[value="' + e.key + '"]');
   if (b) {{ b.click(); }}
 }});
</script>
"""

# NOTE: this template goes through str.format, so every literal CSS brace is
# doubled. The single-brace version raised KeyError on the very last screen —
# after the whole review was done, which is the worst possible moment to lose.
DONE_PAGE = """<!doctype html><meta charset="utf-8"><title>review complete</title>
<style>body{{font:15px/1.6 ui-sans-serif,system-ui,sans-serif;margin:60px auto;
max-width:640px;background:#0d1117;color:#c9d1d9}}code{{background:#161b22;
padding:2px 6px;border-radius:4px}}</style>
<h1>All {total} classified.</h1>
<p>{undo}</p>
<p>Now, in this order — the order is the protocol:</p>
<ol>
 <li>commit <code>study-artifacts/review_sample.jsonl</code></li>
 <li>then <code>python -m study tally</code> — this reads the unblinding key</li>
 <li>then <code>python -m study report</code></li>
</ol>
<p>Committing the classifications before touching the key is what makes the
number defensible. You can stop the server.</p>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    rows = []

    def log_message(self, *a):
        pass

    def _send(self, body, code=200):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        rows = Handler.rows

        # Undo exists because an answer saves instantly with no confirmation, so
        # a mis-keyed card used to be permanent — and a wrong classification is
        # indistinguishable from a considered one once it is in the file.
        if self.path.startswith("/undo"):
            last = _last_answered(rows)
            if last:
                last["classification"] = ""
                last["note"] = ""
                last.pop("answered_at", None)
                _save(rows)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return

        pending = [r for r in rows if not str(r.get("classification", "")).strip()]
        done, total = len(rows) - len(pending), len(rows)
        if not pending:
            return self._send(DONE_PAGE.format(total=total,
                                               undo=_undo_link(rows)))

        r = pending[0]
        buttons = "".join(
            f'<button name="classification" value="{k}"><kbd>{k}</kbd>'
            f'<b>{html.escape(label)}</b> — <i>{html.escape(desc)}</i></button>'
            for k, label, desc in RUBRIC)
        body = (r.get("body") or "").strip()
        body_block = (f'<div class="body">{html.escape(body[:4000])}</div>'
                      if body else
                      '<div class="body meta">[no pull request description]</div>')
        self._send(PAGE.format(
            done=done, total=total, pct=round(100 * done / total, 1),
            rid=r["review_id"], title=html.escape(r.get("title", "")),
            url=html.escape(r.get("url", "")),
            changed_lines=r.get("changed_lines", "?"),
            body_block=body_block, diff=_render_diff(_diff_for(r)),
            buttons=buttons, undo=_undo_link(rows)))

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        import urllib.parse
        form = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8"))
        rid = form.get("rid", [""])[0]
        cls = form.get("classification", [""])[0]
        note = form.get("note", [""])[0]

        for r in Handler.rows:
            if r["review_id"] == rid:
                r["classification"] = cls
                r["note"] = note
                r["answered_at"] = time.time()   # so undo knows which was last
                break
        _save(Handler.rows)          # after every single answer, not at the end

        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()


def serve(port=8731, open_browser=True, sheet=None):
    global SHEET
    if sheet:
        SHEET = pathlib.Path(sheet)
    if not SHEET.exists():
        raise SystemExit(f"no review sheet at {SHEET} — run "
                         f"`python -m study review` first")
    Handler.rows = _load()
    done = sum(1 for r in Handler.rows
               if str(r.get("classification", "")).strip())
    url = f"http://127.0.0.1:{port}/"
    print(f"blind review: {done}/{len(Handler.rows)} already classified")
    print(f"  sheet: {SHEET}")
    print(f"  {url}   (keys 1-6, saved after every answer, undoable, close and "
          f"resume any time)")
    print(f"  the instrument's verdicts are NOT loaded by this server")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped — progress is saved")
