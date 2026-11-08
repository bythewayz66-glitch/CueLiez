"""Live, officer-only cue dashboard (real-time, subject not shown).

A small stdlib HTTP server that serves a browser page which polls for cues and
renders them as they arrive. The subject is never shown this stream. No external
dependencies.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

_DASHBOARD_HTML = """<!DOCTYPE html>
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
async function refresh() {
  try {
    const r = await fetch('/cues');
    const data = await r.json();
    const cues = data.cues || [];
    const status = document.getElementById('status');
    status.textContent = 'Cues: ' + cues.length + ' (updated ' + new Date().toLocaleTimeString() + ')';
    const container = document.getElementById('cues');
    if (!cues.length) { container.innerHTML = '<p class="empty">No observation cues at current thresholds.</p>'; return; }
    container.innerHTML = cues.map(c => {
      const prio = (c.priority || 'medium').toLowerCase();
      const icon = {low:'·',medium:'▲',high:'◆',critical:'●'}[prio] || '·';
      let html = '<div class="cue"><div class="prio ' + prio + '">' + icon + ' ' + prio.toUpperCase() + '</div>';
      if (c.turn_index != null) html += '<div class="meta">Turn ' + c.turn_index + '</div>';
      html += '<div>' + (c.message || '') + '</div>';
      html += '<div class="meta">score=' + (c.score!=null?c.score.toFixed(2):'') + ' · ' + (c.category||'') + ' · ' + (c.cue_id||'') + '</div>';
      if (c.source_quotes && c.source_quotes.length) {
        html += '<div class="src">Source: ' + c.source_quotes.map(q => '"' + (q.quote||'') + '" (T' + (q.turn_index!=null?q.turn_index:'?') + ')').join(' ; ') + '</div>';
      }
      html += '</div>';
      return html;
    }).join('');
  } catch (e) {
    document.getElementById('status').textContent = 'Error: ' + e;
  }
}
setInterval(refresh, 1000);
refresh();
</script>
</body>
</html>
"""


class LiveDashboardServer:
    """Threaded HTTP server exposing a live officer-only cue dashboard."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self._lock = threading.Lock()
        self._cues: List[Dict[str, Any]] = []
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._server is not None:
            return
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/":
                    body = _DASHBOARD_HTML.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if parsed.path == "/cues":
                    with outer._lock:
                        payload = {"cues": list(outer._cues)}
                    body = json.dumps(payload).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self):  # noqa: N802
                parsed = urlparse(self.path)
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
                    body = json.dumps({"ok": True, "count": len(outer._cues)}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(404)
                self.end_headers()

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
