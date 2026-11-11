"""Live, officer-only cue dashboard (real-time, subject not shown).

A small stdlib HTTP server that serves a browser page which polls for cues and
renders them as they arrive. The subject is never shown this stream. No external
dependencies.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CueLiez Officer Dashboard (observation cues only)</title>
<style>
body { font-family: system-ui, sans-serif; margin: 1rem; background:#0b0f14; color:#e6edf3; }
h1 { font-size:1.1rem; }
.notice { background:#1f2937; padding:.75rem; border-radius:.5rem; margin-bottom:1rem; font-size:.9rem; }
.cue { border:1px solid #374151; border-radius:.5rem; padding:.75rem; margin:.5rem 0; }
.prio { font-weight:700; }
.high { color:#f472b6; } .medium { color:#fbbf24; } .low { color:#34d399; } .critical { color:#f87171; }
.meta { color:#9ca3af; font-size:.8rem; }
.src { color:#93c5fd; font-size:.8rem; margin-top:.25rem; }
.empty { color:#9ca3af; font-style:italic; }
</style>
</head>
<body>
<h1>CueLiez — Officer Cue Dashboard</h1>
<div class="notice">Officer-only view. The subject is not shown this stream. Cues are probabilistic observations for professional review — not findings, diagnoses, or determinations.</div>
<div id="status" class="meta">Connecting…</div>
<div id="cues"></div>
<script>
const CONTROL = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u200e\u200f\u061c\u2028\u2029\u202a-\u202e\u2066-\u2069]/g;
const PRIORITIES = ['low', 'medium', 'high', 'critical'];
const ICONS = {low: '·', medium: '▲', high: '◆', critical: '●'};
function vis(v) {
  if (v == null) return '';
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
  return s.replace(CONTROL, ch => '[U+' + ch.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0') + ']');
}
function node(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
function quoteText(q) {
  if (q == null || typeof q !== 'object') return '"' + vis(q) + '" (T?)';
  return '"' + vis(q.quote || q.text || '') + '" (T' + (q.turn_index != null ? vis(q.turn_index) : '?') + ')';
}
function cueNode(c) {
  c = c && typeof c === 'object' ? c : {};
  const prio = vis(c.priority || 'medium').toLowerCase();
  const known = PRIORITIES.indexOf(prio) >= 0;
  const card = node('div', 'cue');
  card.append(node('div', 'prio' + (known ? ' ' + prio : ''), (ICONS[prio] || '·') + ' ' + prio.toUpperCase()));
  if (c.turn_index != null) card.append(node('div', 'meta', 'Turn ' + vis(c.turn_index)));
  card.append(node('div', null, vis(c.message)));
  const score = typeof c.score === 'number' && isFinite(c.score) ? c.score.toFixed(2) : '';
  card.append(node('div', 'meta', 'score=' + score + ' · ' + vis(c.category) + ' · ' + vis(c.cue_id)));
  if (Array.isArray(c.source_quotes) && c.source_quotes.length) {
    card.append(node('div', 'src', 'Source: ' + c.source_quotes.map(quoteText).join(' ; ')));
  }
  return card;
}
async function refresh() {
  try {
    const r = await fetch('/cues');
    const data = await r.json();
    const cues = Array.isArray(data.cues) ? data.cues : [];
    const status = document.getElementById('status');
    status.textContent = 'Cues: ' + cues.length + ' (updated ' + new Date().toLocaleTimeString() + ')';
    const container = document.getElementById('cues');
    if (!cues.length) { container.replaceChildren(node('p', 'empty', 'No observation cues at current thresholds.')); return; }
    container.replaceChildren(...cues.map(cueNode));
  } catch (e) {
    document.getElementById('status').textContent = 'Error: ' + vis(e);
  }
}
setInterval(refresh, 1000);
refresh();
</script>
</body>
</html>
"""


def _csp_for(page: str) -> str:
    def digest(body: str) -> str:
        return "'sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii") + "'"

    scripts = " ".join(digest(m) for m in re.findall(r"<script[^>]*>(.*?)</script>", page, re.S))
    styles = " ".join(digest(m) for m in re.findall(r"<style[^>]*>(.*?)</style>", page, re.S))
    return (
        f"default-src 'none'; script-src {scripts}; style-src {styles}; connect-src 'self'; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )


_DASHBOARD_CSP = _csp_for(_DASHBOARD_HTML)
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class _RateLimiter:
    def __init__(self, limit: int = 120, window_s: float = 60.0):
        self.limit = limit
        self.window_s = window_s
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            q = [t for t in self._hits.get(key, []) if now - t < self.window_s]
            if len(q) >= self.limit:
                self._hits[key] = q
                return False
            q.append(now)
            self._hits[key] = q
            return True


class LiveDashboardServer:
    """Threaded HTTP server exposing a live officer-only cue dashboard."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0, *, token: Optional[str] = None, rate_limit: int = 120):
        self.host = host
        self.port = port
        self.token = (token if token is not None else __import__("os").environ.get("CUELIEZ_DASHBOARD_TOKEN", "")).strip() or None
        self._allowed_origins = [o.strip() for o in __import__("os").environ.get("CUELIEZ_DASHBOARD_ALLOWED_ORIGINS", "").split(",") if o.strip()]
        self._lock = threading.Lock()
        self._cues: List[Dict[str, Any]] = []
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._rate = _RateLimiter(limit=max(1, int(rate_limit)))

    def start(self) -> None:
        if self._server is not None:
            return
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _authorized(self) -> bool:
                if not outer.token:
                    return True
                auth = self.headers.get("Authorization", "")
                if auth == f"Bearer {outer.token}":
                    return True
                if self.headers.get("X-CueLiez-Token") == outer.token:
                    return True
                parsed = urlparse(self.path)
                q = urllib.parse.parse_qs(parsed.query)
                return (q.get("token") or [None])[0] == outer.token

            def _origin_ok(self) -> bool:
                origin = self.headers.get("Origin")
                if not origin:
                    return True  # non-browser/programmatic clients
                if origin in outer._allowed_origins:
                    return True
                try:
                    u = urlparse(origin)
                    return u.scheme in ("http", "https") and u.hostname in _LOCAL_HOSTS and not u.path.strip("/")
                except ValueError:
                    return False

            def _rate_ok(self) -> bool:
                key = self.client_address[0] if self.client_address else "unknown"
                return outer._rate.allow(key)

            def _respond(self, code: int, body: bytes = b"", content_type: Optional[str] = None, csp: Optional[str] = None) -> None:
                self.send_response(code)
                if content_type:
                    self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                if csp:
                    self.send_header("Content-Security-Policy", csp)
                self.end_headers()
                self.wfile.write(body)

            def _json(self, code: int, payload: Any) -> None:
                self._respond(code, json.dumps(payload).encode("utf-8"), "application/json")

            def _unauthorized(self) -> None:
                self._json(401, {"ok": False, "error": "unauthorized"})

            def _forbidden(self, msg: str = "forbidden") -> None:
                self._json(403, {"ok": False, "error": msg})

            def _rate_limited(self) -> None:
                self._json(429, {"ok": False, "error": "rate_limited"})

            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                if not self._rate_ok():
                    self._rate_limited(); return
                if not self._authorized():
                    self._unauthorized(); return
                if not self._origin_ok():
                    self._forbidden("origin_not_allowed"); return
                if parsed.path == "/":
                    self._respond(200, _DASHBOARD_HTML.encode("utf-8"), "text/html; charset=utf-8", csp=_DASHBOARD_CSP)
                    return
                if parsed.path == "/cues":
                    with outer._lock:
                        payload = {"cues": list(outer._cues)}
                    self._json(200, payload)
                    return
                self._respond(404)

            def do_POST(self):  # noqa: N802
                parsed = urlparse(self.path)
                if not self._rate_ok():
                    self._rate_limited(); return
                if not self._authorized():
                    self._unauthorized(); return
                if not self._origin_ok():
                    self._forbidden("origin_not_allowed"); return
                if parsed.path == "/cues":
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length) if length else b""
                    try:
                        data = json.loads(raw.decode("utf-8")) if raw else {}
                    except Exception:
                        data = {}
                    cues = data.get("cues", data.get("observations", []))
                    if not isinstance(cues, list):
                        cues = []
                    with outer._lock:
                        outer._cues = [c for c in cues if isinstance(c, dict)]
                        count = len(outer._cues)
                    self._json(200, {"ok": True, "count": count})
                    return
                self._respond(404)

            def log_message(self, *args):  # noqa: D401
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def push_cues(self, cues: Sequence[Any]) -> None:
        with self._lock:
            self._cues = [c if isinstance(c, dict) else {} for c in cues]

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def __enter__(self) -> "LiveDashboardServer":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
