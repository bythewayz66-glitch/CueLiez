"""Real web frontend for CueLiez (officer-only, localhost by default).

A stdlib-only HTTP server that operates the real Python pipeline — ingest,
observation runners / cue packs, cue rendering, officer notes, gated sealing,
export and package verification. Nothing here is a simulation: every cue
shown comes from a pipeline run on the transcript the operator submitted.

Safety: observation cues only, never findings. All user / transcript / cue
text is HTML-escaped server-side (delivery/safe.py); pages carry a CSP,
an Origin check, optional token auth and rate limiting, following the
patterns in delivery/dashboard.py and training_gui.py.
"""

from __future__ import annotations

import html
import json
import os
import threading
import time
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from .compliance.training import get_training_bundle
from .delivery import attach_officer_cue_notes, cues_from_observations
from .delivery.safe import csp_policy_for, escape_html
from .export import (
    render_package_summary_html,
    render_package_summary_markdown,
)
from .gates import (
    DISCLAIMER,
    GateError,
    SessionGateState,
    export_sealed_package_json,
    filter_observations_by_consent,
    record_consent,
    record_dual_acknowledge,
    verify_package_hash,
)
from .observations import default_runner, full_runner
from .observations.assisted import (
    clear_assisted_registry,
    make_multi_signal_assisted_adapter,
    merge_assisted_observations,
    register_assisted_observer,
)
from .packs import get_pack, list_packs
from .session import assert_can_observe, seal
from .signing import hmac_signer, load_signing_key, verify_hmac_signature

HONEST_NOTICE = (
    "CueLiez observes transcript/text signals and produces observation cues for human review. "
    "It does not determine credibility or produce findings. Gates and human judgment remain required."
)
NOTICE = "Observation cues only, not findings — human judgment remains required."
MAX_BODY_BYTES = 5 * 1024 * 1024
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

_SAMPLE_TRANSCRIPT = """[
  {"role": "officer", "text": "Can you walk me through where you were that evening?"},
  {"role": "subject", "text": "I think maybe I was around the area, you know, doing stuff.", "response_latency_ms": 4200},
  {"role": "officer", "text": "What specific location and time?"},
  {"role": "subject", "text": "I don't really remember exactly. I already told you I was not there.", "response_latency_ms": 3100},
  {"role": "officer", "text": "Earlier you said you were around the area. Can you clarify?"},
  {"role": "subject", "text": "I mean nearby, not exactly there. It was probably around 8 or 9."}
]"""


# ---------------------------------------------------------------------------
# Transcript / NDJSON helpers (same per-line behaviour as the CLI stream mode:
# blank lines skipped, dict turns normalised, list lines expanded, malformed
# lines reported per line and skipped — never aborting the whole stream).
# ---------------------------------------------------------------------------

def _normalize_turn(turn: Any) -> Any:
    if not isinstance(turn, dict):
        return turn
    if "role" not in turn and "speaker" in turn:
        out = dict(turn)
        out["role"] = out.get("speaker")
        return out
    return turn


def parse_ndjson_turns(text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Parse NDJSON turns. Returns (turns, errors); errors are per-line.

    Each error is {"line": <1-based line number>, "error": <message>}.
    """
    turns: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:  # malformed line: report and skip
            errors.append({"line": lineno, "error": f"invalid JSON: {e}"})
            continue
        if isinstance(obj, dict):
            turns.append(_normalize_turn(obj))
        elif isinstance(obj, list):
            for t in obj:
                turns.append(_normalize_turn(t))
        else:
            errors.append({"line": lineno, "error": "turn must be a JSON object (or array of objects)"})
    return turns, errors


def parse_transcript_input(data: Any) -> List[Dict[str, Any]]:
    """Accept a JSON array of turns, or an object with 'transcript'/'turns'."""
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, dict):
        if "transcript" in data:
            data = data["transcript"]
        elif "turns" in data:
            data = data["turns"]
    if isinstance(data, list):
        return [_normalize_turn(t) for t in data]
    raise ValueError(
        "Transcript input must be a JSON array of turns, or an object with a 'transcript' or 'turns' array."
    )


# ---------------------------------------------------------------------------
# Real pipeline driver (mirrors cli.run_cli, minus stdout/connector paths).
# ---------------------------------------------------------------------------

def _high_priority_cue_ids(cues) -> List[str]:
    return [c.cue_id for c in cues if getattr(c, "priority", "") in {"high", "critical"}]


def run_pipeline(
    transcript: Sequence[Dict[str, Any]],
    *,
    pack: Optional[str] = None,
    mode: str = "generic",
    runner: str = "default",
    consent: bool = False,
    attested_by: Optional[str] = None,
    subject_id: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    training_ack: bool = False,
    training_version: Optional[str] = None,
    intended_uses: Optional[List[str]] = None,
    enable_assisted: bool = False,
    min_score: float = 0.0,
    max_cues: Optional[int] = None,
    officer_notes: Optional[Any] = None,
    do_seal: bool = False,
    sign: bool = False,
    high_priority_cue_ids: Optional[List[str]] = None,
    dual_control: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run the real pipeline on a transcript. Raises GateError / ValueError.

    Returns a dict with cues (dicts), observations, package (unsealed unless
    do_seal), gate state, and counts. The caller keeps the returned
    ``_gate_state`` (a SessionGateState) for a later separate seal call.
    """
    transcript = [_normalize_turn(t) for t in transcript]
    annotations: Dict[str, Any] = {
        "mode": mode,
        "intended_uses": list(intended_uses or []),
        "operator_notice": HONEST_NOTICE,
    }
    if pack:
        cue_pack = get_pack(pack)
        state = cue_pack.make_gate_state(
            intended_uses=list(intended_uses or []),
            jurisdiction=jurisdiction,
            subject_id=subject_id,
        )
        annotations["cue_pack"] = cue_pack.id
        annotations["cue_pack_mode"] = cue_pack.mode
        if mode != "generic":
            state.mode = mode
        else:
            mode = state.mode
            annotations["mode"] = state.mode
    else:
        cue_pack = None
        state = SessionGateState(
            mode=mode,  # type: ignore[arg-type]
            intended_uses=list(intended_uses or []),
            jurisdiction=jurisdiction,
            subject_id=subject_id,
        )

    if consent:
        if not (attested_by or "").strip():
            raise GateError("consent_attester_required", "Consent requires a non-empty attester.")
        record_consent(state, attested_by=attested_by, subject_id=subject_id, jurisdiction=jurisdiction)
    elif attested_by:
        # An attester alone is not consent; record it only with consent.
        state.consent_attested_by = attested_by
    if training_ack or training_version:
        state.training_acknowledged = True
        if training_version:
            state.training_version = training_version

    # Fail closed before observation, exactly like the CLI.
    assert_can_observe(state)

    if cue_pack is not None:
        raw_package = cue_pack.build_package(transcript, annotations=annotations)
        observations = raw_package.get("observations") or []
    else:
        obs_runner = full_runner() if runner == "full" else default_runner()
        raw_package = obs_runner.build_package(transcript, annotations=annotations)
        observations = raw_package.get("observations") or []

    if enable_assisted:
        clear_assisted_registry()
        register_assisted_observer("multi_signal", make_multi_signal_assisted_adapter())
        observations = merge_assisted_observations(observations, transcript, enabled=True)
        if isinstance(raw_package, dict):
            raw_package["observations"] = observations

    # Same consent filter as the CLI: feature-derived observations must not
    # fire without the corresponding modality/demographic consent. Text
    # observations pass through unchanged.
    observations = filter_observations_by_consent(observations, state)
    if isinstance(raw_package, dict):
        raw_package["observations"] = observations

    cues = cues_from_observations(
        observations, min_score=min_score, max_cues=max_cues, transcript=transcript
    )
    hi_ids = _high_priority_cue_ids(cues)

    package = dict(raw_package)
    if officer_notes is not None:
        notes = officer_notes
        if isinstance(notes, dict) and "officer_cue_notes" in notes:
            notes = notes["officer_cue_notes"]
        package = attach_officer_cue_notes(package, notes)

    if dual_control:
        for rec in dual_control:
            record_dual_acknowledge(
                state,
                str(rec.get("cue_id") or ""),
                str(rec.get("first_officer_id") or rec.get("first_officer") or ""),
                str(rec.get("second_officer_id") or rec.get("second_officer") or ""),
                notes=str(rec.get("notes") or ""),
            )

    sealed = False
    if do_seal:
        dual_ids = list(high_priority_cue_ids or []) or (hi_ids if state.mode == "government" else [])
        signer = None
        if sign:
            if load_signing_key() is None:
                raise GateError(
                    "signing_key_missing",
                    "Signing requires CUELIEZ_SIGNING_KEY or CUELIEZ_SIGNING_KEY_FILE.",
                )
            signer = hmac_signer()
        package = seal(package, state, high_priority_cue_ids=dual_ids, signer=signer)
        sealed = True

    return {
        "ok": True,
        "notice": HONEST_NOTICE,
        "cue_count": len(cues),
        "observation_count": len(observations),
        "high_priority_cue_ids": hi_ids,
        "sealed": sealed,
        "cues": [c.to_dict() for c in cues],
        "observations": observations,
        "transcript": list(transcript),
        "package": package,
        "gate_state": state.to_dict(),
        "_gate_state": state,
    }


def verify_package(package: Any) -> Dict[str, Any]:
    """Verify a sealed package: hash + HMAC signature when present."""
    if not isinstance(package, dict):
        return {"ok": False, "hash_ok": False, "error": "package must be a JSON object"}
    hash_ok = verify_package_hash(package)
    sig: Any = {"ok": None, "reason": "no_signature"}
    if package.get("package_signature"):
        sig = verify_hmac_signature(package)
        if isinstance(sig, dict) and sig.get("reason") == "signing_key_missing" and load_signing_key() is None:
            sig = {"ok": None, "reason": "signing_key_not_configured"}
    ok = bool(hash_ok) and (sig.get("ok") is not False)
    return {
        "ok": ok,
        "hash_ok": bool(hash_ok),
        "signature": sig,
        "package_hash": package.get("package_hash"),
        "notice": HONEST_NOTICE,
    }


# ---------------------------------------------------------------------------
# HTML rendering (server-side, everything escaped via delivery/safe.py).
# ---------------------------------------------------------------------------

_STYLE = (
    "body{font-family:system-ui,sans-serif;margin:0;background:#0b1020;color:#e8eefc}"
    "a{color:#8fd3ff} header{padding:14px 20px;background:#121a33;border-bottom:1px solid #26325f}"
    "main{padding:20px;max-width:1100px;margin:0 auto}"
    ".card{background:#121a33;border:1px solid #26325f;border-radius:12px;padding:14px;margin:12px 0}"
    ".notice{background:#3a2f00;border:1px solid #8a6d00;border-radius:8px;padding:10px;margin:12px 0}"
    ".btn{display:inline-block;padding:8px 12px;border-radius:8px;background:#234;border:1px solid #456;color:#e8eefc;text-decoration:none;cursor:pointer}"
    ".btn.primary{background:#1f5eff;border-color:#4c7dff}"
    ".muted{color:#a8b4d8} .ok{color:#7dffb3} .bad{color:#ff8f8f}"
    "textarea,input,select{width:100%;box-sizing:border-box;padding:8px;border-radius:8px;border:1px solid #456;background:#091022;color:#e8eefc}"
    "table{width:100%;border-collapse:collapse} th,td{border:1px solid #26325f;padding:8px;vertical-align:top;text-align:left}"
    "code{overflow-wrap:anywhere} pre{white-space:pre-wrap;background:#091022;padding:10px;border-radius:8px;border:1px solid #26325f}"
    "nav a{margin-right:10px} label{font-weight:600;display:block;margin-top:10px}"
)


def _page(title: str, body: str) -> bytes:
    doc = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{escape_html(title)}</title><style>{_STYLE}</style></head><body>"
        "<header><strong>CueLiez Web Frontend</strong> "
        "<span class=\"muted\">— operate the real pipeline; observation cues only.</span>"
        "<nav><a href=\"/\">Operate</a><a href=\"/training\">Training</a>"
        "<a href=\"/api/packs\">Packs (JSON)</a></nav></header>"
        f"<main>{body}</main></body></html>"
    )
    return doc.encode("utf-8")


def _csp_for_page(page: bytes) -> str:
    text = page.decode("utf-8")
    csp = csp_policy_for(text)
    return csp.replace("form-action 'none'", "form-action 'self'")


def _home_body(packs: List[Dict[str, Any]]) -> str:
    pack_opts = "".join(
        f"<option value=\"{escape_html(p['id'])}\">{escape_html(p['id'])} — {escape_html(p['name'])}</option>"
        for p in packs
    )
    return f"""
<div class="notice"><strong>{escape_html(NOTICE)}</strong><br>{escape_html(HONEST_NOTICE)}</div>
<div class="card"><h2>Operate — run the real pipeline</h2>
<p class="muted">Paste a transcript (JSON array of turns) or upload a transcript JSON file, choose a pack and mode, record consent/training, then Run. Every cue shown comes from the pipeline run on your transcript — no canned cues.</p>
<form action="/run" method="post" enctype="multipart/form-data">
<label>Transcript JSON (array of turns)</label>
<textarea name="transcript" rows="10">{escape_html(_SAMPLE_TRANSCRIPT)}</textarea>
<label>Or upload a transcript JSON file</label>
<input type="file" name="transcript_file">
<label>Cue pack (optional — empty uses the runner)</label>
<select name="pack"><option value="">— runner (no pack) —</option>{pack_opts}</select>
<label>Mode</label>
<select name="mode">
<option value="generic">generic</option><option value="interrogation">interrogation</option>
<option value="therapy">therapy</option><option value="clinical">clinical</option>
<option value="government">government</option></select>
<label>Runner (when no pack)</label>
<select name="runner"><option value="default">default</option><option value="full">full</option></select>
<label><input type="checkbox" name="consent" value="1" style="width:auto"> Record affirmative consent</label>
<label>Consent attester (officer/clinician ID — required for gated modes)</label>
<input name="attested_by" placeholder="officer-a">
<label>Subject / session ID (optional)</label><input name="subject_id">
<label>Jurisdiction (optional)</label><input name="jurisdiction">
<label><input type="checkbox" name="training_ack" value="1" style="width:auto"> Training acknowledged</label>
<label>Training version (required for gated modes)</label><input name="training_version" placeholder="v1">
<label><input type="checkbox" name="enable_assisted" value="1" style="width:auto"> Enable assisted (multi-signal) observers — opt-in, off by default</label>
<label>Min cue score</label><input name="min_score" value="0.0">
<label>Max cues (optional)</label><input name="max_cues" placeholder="">
<label>Officer cue notes (JSON list, attached before sealing — optional)</label>
<textarea name="officer_notes" rows="3" placeholder='[{{"cue_id": "...", "action": "noted", "note": "...", "officer_id": "officer-a"}}]'></textarea>
<label><input type="checkbox" name="seal" value="1" style="width:auto"> Seal the package after the run (gates enforced)</label>
<button class="btn primary" type="submit">Run pipeline</button>
</form></div>
<div class="card"><h2>Stream turns (NDJSON)</h2>
<p class="muted">Post one JSON turn per line. Malformed lines are reported per line and skipped; valid turns are processed and new cues returned.</p>
<form action="/stream" method="post">
<label>NDJSON turns (one JSON object per line)</label>
<textarea name="ndjson" rows="6">{{"role": "subject", "text": "I think maybe I was around the area."}}
{{"role": "subject", "text": "I don't really remember exactly."}}
not json at all</textarea>
<label>Session ID (optional — re-use to accumulate turns across posts)</label>
<input name="session_id" placeholder="stream-1">
<button class="btn" type="submit">Stream turns</button></form></div>
<div class="card"><h2>Verify a sealed package</h2>
<p class="muted">Paste a sealed package JSON; the server runs the real hash check (and HMAC check when a signature is present).</p>
<form action="/verify" method="post">
<label>Sealed package JSON</label><textarea name="package" rows="6" placeholder='{{"package_hash": "...", ...}}'></textarea>
<button class="btn" type="submit">Verify package</button></form></div>
<div class="card"><h2>Exports</h2>
<p class="muted">After a sealed run, download the package: <a href="/export?format=json">JSON</a> · <a href="/export?format=md">Markdown</a> · <a href="/export?format=html">HTML</a>. Exports use the real export renderers.</p>
<p class="muted">API: <code>POST /api/run</code> (JSON), <code>POST /api/stream</code> (NDJSON body), <code>POST /api/verify</code> (JSON), <code>POST /api/seal</code>, <code>POST /api/notes</code>, <code>GET /api/export?format=json|md|html</code>, <code>GET /api/training</code>, <code>GET /api/packs</code>.</p></div>
"""


def _cue_rows(cues: List[Dict[str, Any]]) -> str:
    rows = []
    for c in cues:
        quotes = ""
        for q in c.get("source_quotes") or []:
            ti = q.get("turn_index")
            where = f"T{ti}" if ti is not None else "source"
            quotes += f"{where}: &ldquo;{escape_html(q.get('text') or '')}&rdquo; "
        rows.append(
            "<tr><td>" + escape_html(c.get("priority") or "") + "</td>"
            "<td>" + escape_html(c.get("turn_index")) + "</td>"
            "<td><code>" + escape_html(c.get("cue_id") or "") + "</code></td>"
            "<td>" + escape_html(c.get("label") or "") + "</td>"
            "<td>" + escape_html(f"{float(c.get('score') or 0):.2f}") + "</td>"
            "<td><code>" + escape_html(c.get("method") or "") + "</code></td>"
            "<td>" + escape_html(c.get("message") or "") + "</td>"
            "<td>" + quotes + "</td></tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='8'>No observation cues at current thresholds.</td></tr>"


def _result_body(result: Dict[str, Any]) -> str:
    pkg = result.get("package") or {}
    cues = result.get("cues") or []
    obs = result.get("observations") or []
    model_ids = sorted({str((o.get("confidence") or {}).get("model_id") or o.get("method") or "") for o in obs if isinstance(o, dict)})
    model_ids = [m for m in model_ids if m]
    seal_line = (
        f"Sealed — package hash <code>{escape_html(pkg.get('package_hash') or '')}</code>"
        if result.get("sealed")
        else "Not sealed (unsealed run)."
    )
    return f"""
<div class="notice"><strong>{escape_html(NOTICE)}</strong></div>
<div class="card"><h2>Run result</h2>
<p>Cues: <strong>{len(cues)}</strong> · Observations: <strong>{len(obs)}</strong> · {seal_line}</p>
<p class="muted">Gate state: mode <code>{escape_html((result.get('gate_state') or {}).get('mode') or '')}</code> · consent <code>{escape_html((result.get('gate_state') or {}).get('consent'))}</code> · training acknowledged <code>{escape_html((result.get('gate_state') or {}).get('training_acknowledged'))}</code></p>
<p class="muted">Observation model IDs: {escape_html(', '.join(model_ids))}</p>
<p><a class="btn" href="/">Back to Operate</a>
<a class="btn" href="/export?format=json">Export JSON</a>
<a class="btn" href="/export?format=md">Export Markdown</a>
<a class="btn" href="/export?format=html">Export HTML</a></p>
<form action="/api/seal" method="post" style="display:inline"><button class="btn" type="submit">Seal last run (API)</button></form>
</div>
<div class="card"><h2>Observation cues (for human review)</h2>
<table><thead><tr><th>Priority</th><th>Turn</th><th>Cue ID</th><th>Label</th><th>Score</th><th>Method / model</th><th>Message</th><th>Source (transcript)</th></tr></thead>
<tbody>{_cue_rows(cues)}</tbody></table></div>
<div class="card"><h2>Observations</h2><pre>{escape_html(json.dumps(obs, indent=2, ensure_ascii=False, default=str))}</pre></div>
"""


def _error_body(code: str, message: str) -> str:
    return f"""
<div class="notice"><strong>{escape_html(NOTICE)}</strong></div>
<div class="card"><h2>Run failed — gate / input error</h2>
<p><strong>Error code:</strong> <code>{escape_html(code)}</code></p>
<p>{escape_html(message)}</p>
<p><a class="btn" href="/">Back to Operate</a></p></div>
"""


def _training_body() -> str:
    cards = []
    for m in get_training_bundle():
        def _sec(name: str, items: List[str]) -> str:
            lis = "".join(f"<li>{escape_html(x)}</li>" for x in items)
            return f"<h3>{escape_html(name)}</h3><ul>{lis}</ul>"
        cards.append(
            f"<div class='card'><h3>{escape_html(m.title)}</h3>"
            f"<p class='muted'>ID: <code>{escape_html(m.id)}</code> · Version: {escape_html(m.version)} · Domain: {escape_html(m.domain)} · Mode: {escape_html(m.mode)}</p>"
            f"{_sec('Objectives', m.objectives)}"
            f"{_sec('Required topics', m.required_topics)}"
            f"{_sec('Operator responsibilities', m.operator_responsibilities)}"
            f"{_sec('Assessment checks', m.assessment_checks)}"
            f"<p class='muted'>Interactive module, quiz and sandbox live in the Training GUI: <a href='http://127.0.0.1:911/'>http://127.0.0.1:911/</a> (start with <code>cueliez --training-gui</code>).</p></div>"
        )
    return (
        f"<div class='notice'><strong>{escape_html(NOTICE)}</strong></div>"
        "<div class='card'><h2>Training modules</h2>"
        "<p class='muted'>Read live from the real training bundle (compliance/training.py — get_training_bundle). "
        "Training acknowledgement + version are required for gated modes before observation or sealing.</p></div>"
        + "".join(cards)
    )


# ---------------------------------------------------------------------------
# Rate limiter (same shape as delivery/dashboard.py).
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class WebFrontendServer:
    """Threaded stdlib HTTP server operating the real CueLiez pipeline."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0, *, token: Optional[str] = None, rate_limit: int = 120):
        self.host = host
        self.port = port
        self.token = (token if token is not None else os.environ.get("CUELIEZ_WEB_TOKEN", "")).strip() or None
        self._allowed_origins = [
            o.strip() for o in os.environ.get("CUELIEZ_WEB_ALLOWED_ORIGINS", "").split(",") if o.strip()
        ]
        self._lock = threading.Lock()
        self._last_run: Optional[Dict[str, Any]] = None
        self._streams: Dict[str, Dict[str, Any]] = {}
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._rate = _RateLimiter(limit=max(1, int(rate_limit)))

    # -- state helpers ------------------------------------------------------
    def _store_last(self, result: Dict[str, Any]) -> None:
        with self._lock:
            self._last_run = result

    def _get_last(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._last_run

    # -- server lifecycle ---------------------------------------------------
    def start(self) -> None:
        if self._server is not None:
            return
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # noqa: D401
                return

            # -- guards ------------------------------------------------------
            def _authorized(self) -> bool:
                if not outer.token:
                    return True
                auth = self.headers.get("Authorization", "")
                if auth == f"Bearer {outer.token}":
                    return True
                if self.headers.get("X-CueLiez-Token") == outer.token:
                    return True
                q = urllib.parse.parse_qs(urlparse(self.path).query)
                return (q.get("token") or [None])[0] == outer.token

            def _origin_ok(self) -> bool:
                origin = self.headers.get("Origin")
                if not origin:
                    return True
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

            # -- responses ---------------------------------------------------
            def _respond(self, code: int, body: bytes = b"", content_type: Optional[str] = None,
                         csp: Optional[str] = None, filename: Optional[str] = None) -> None:
                self.send_response(code)
                if content_type:
                    self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                if csp:
                    self.send_header("Content-Security-Policy", csp)
                if filename:
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def _html(self, code: int, body: str) -> None:
                page = _page("CueLiez Web Frontend", body)
                self._respond(code, page, "text/html; charset=utf-8", csp=_csp_for_page(page))

            def _json(self, code: int, payload: Any) -> None:
                self._respond(code, json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
                              "application/json; charset=utf-8")

            def _gate_error(self, e: GateError) -> None:
                self._json(403, {"ok": False, "error_code": e.code, "error": e.message, "notice": HONEST_NOTICE})

            def _guard(self) -> bool:
                if not self._rate_ok():
                    self._json(429, {"ok": False, "error": "rate_limited"})
                    return False
                if not self._authorized():
                    self._json(401, {"ok": False, "error": "unauthorized"})
                    return False
                if not self._origin_ok():
                    self._json(403, {"ok": False, "error": "origin_not_allowed"})
                    return False
                return True

            # -- body parsing ------------------------------------------------
            def _read_body(self) -> bytes:
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY_BYTES:
                    raise ValueError("request body too large")
                return self.rfile.read(length) if length else b""

            def _read_json_body(self) -> Dict[str, Any]:
                raw = self._read_body()
                if not raw:
                    return {}
                data = json.loads(raw.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("JSON body must be an object")
                return data

            def _read_form(self) -> Dict[str, Any]:
                ctype = self.headers.get("Content-Type") or ""
                if "multipart/form-data" in ctype:
                    import cgi  # stdlib; deprecated in 3.11+ but present in 3.12
                    environ = {
                        "REQUEST_METHOD": "POST",
                        "CONTENT_TYPE": ctype,
                        "CONTENT_LENGTH": self.headers.get("Content-Length") or "0",
                    }
                    form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=environ)
                    out: Dict[str, Any] = {}
                    for key in form.keys():
                        item = form[key]
                        if isinstance(item, list):
                            item = item[0]
                        if getattr(item, "filename", None):
                            raw = item.file.read() if item.file is not None else b""
                            out[key] = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
                        else:
                            out[key] = item.value
                    return out
                raw = self._read_body()
                parsed = urllib.parse.parse_qs(raw.decode("utf-8", errors="replace"))
                return {k: v[0] for k, v in parsed.items() if v}

            # -- option coercion --------------------------------------------
            def _opts(self, data: Dict[str, Any]) -> Dict[str, Any]:
                def _bool(v: Any) -> bool:
                    if isinstance(v, bool):
                        return v
                    return str(v).strip().lower() in {"1", "true", "yes", "on"}

                def _float(v: Any, default: float) -> float:
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        return default

                def _int_or_none(v: Any) -> Optional[int]:
                    if v in (None, ""):
                        return None
                    try:
                        return int(v)
                    except (TypeError, ValueError):
                        return None

                uses = data.get("intended_uses") or data.get("intended_use") or []
                if isinstance(uses, str):
                    uses = [u.strip() for u in uses.split(",") if u.strip()]
                return {
                    "pack": (str(data.get("pack") or "").strip() or None),
                    "mode": str(data.get("mode") or "generic").strip() or "generic",
                    "runner": str(data.get("runner") or "default").strip() or "default",
                    "consent": _bool(data.get("consent", False)),
                    "attested_by": (str(data.get("attested_by") or data.get("consent_attester") or "").strip() or None),
                    "subject_id": (str(data.get("subject_id") or "").strip() or None),
                    "jurisdiction": (str(data.get("jurisdiction") or "").strip() or None),
                    "training_ack": _bool(data.get("training_ack", False)),
                    "training_version": (str(data.get("training_version") or "").strip() or None),
                    "intended_uses": list(uses),
                    "enable_assisted": _bool(data.get("enable_assisted", False)),
                    "min_score": _float(data.get("min_score", 0.0), 0.0),
                    "max_cues": _int_or_none(data.get("max_cues")),
                    "do_seal": _bool(data.get("seal", data.get("do_seal", False))),
                    "sign": _bool(data.get("sign", False)),
                    "high_priority_cue_ids": data.get("high_priority_cue_ids") or None,
                    "dual_control": data.get("dual_control") or None,
                }

            def _public_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
                return {k: v for k, v in result.items() if not k.startswith("_")}

            def _run_from(self, data: Dict[str, Any], transcript: Any) -> Dict[str, Any]:
                opts = self._opts(data)
                turns = parse_transcript_input(transcript)
                notes_raw = data.get("officer_notes")
                notes = None
                if notes_raw not in (None, ""):
                    notes = json.loads(notes_raw) if isinstance(notes_raw, str) else notes_raw
                result = run_pipeline(turns, officer_notes=notes, **opts)
                outer._store_last(result)
                return result

            # -- GET ---------------------------------------------------------
            def do_GET(self):  # noqa: N802
                if not self._guard():
                    return
                parsed = urlparse(self.path)
                path = parsed.path
                try:
                    if path == "/":
                        return self._html(200, _home_body(list_packs()))
                    if path == "/training":
                        return self._html(200, _training_body())
                    if path == "/api/packs":
                        return self._json(200, {"ok": True, "packs": list_packs()})
                    if path == "/api/training":
                        return self._json(200, {"ok": True, "modules": [m.to_dict() for m in get_training_bundle()]})
                    if path == "/api/last":
                        last = outer._get_last()
                        if last is None:
                            return self._json(404, {"ok": False, "error": "no_run_yet"})
                        return self._json(200, self._public_result(last))
                    if path in ("/export", "/api/export"):
                        return self._do_export(parsed)
                    return self._respond(404)
                except Exception as e:  # noqa: BLE001
                    return self._json(500, {"ok": False, "error": str(e)})

            def _do_export(self, parsed) -> None:
                last = outer._get_last()
                if last is None:
                    return self._json(404, {"ok": False, "error": "no_run_yet"})
                pkg = last.get("package") or {}
                if not pkg.get("sealed"):
                    return self._json(409, {"ok": False, "error": "package_not_sealed",
                                             "error_code": "package_not_sealed"})
                fmt = (urllib.parse.parse_qs(parsed.query).get("format") or ["json"])[0].lower()
                cues = last.get("cues") or []
                obs = last.get("observations") or []
                transcript = last.get("transcript") or []
                if fmt == "json":
                    body = export_sealed_package_json(pkg).encode("utf-8")
                    return self._respond(200, body, "application/json; charset=utf-8",
                                         filename="sealed_package.json")
                if fmt == "md":
                    body = render_package_summary_markdown(pkg, cues=cues, observations=obs,
                                                           transcript=transcript).encode("utf-8")
                    return self._respond(200, body, "text/markdown; charset=utf-8",
                                         filename="sealed_package.summary.md")
                if fmt == "html":
                    body = render_package_summary_html(pkg, cues=cues, observations=obs,
                                                       transcript=transcript).encode("utf-8")
                    return self._respond(200, body, "text/html; charset=utf-8",
                                         filename="sealed_package.summary.html")
                return self._json(400, {"ok": False, "error": "unknown format (json|md|html)"})

            # -- POST --------------------------------------------------------
            def do_POST(self):  # noqa: N802
                if not self._guard():
                    return
                parsed = urlparse(self.path)
                path = parsed.path
                try:
                    if path == "/api/run":
                        data = self._read_json_body()
                        transcript = data.get("transcript")
                        if transcript is None:
                            return self._json(400, {"ok": False, "error": "transcript is required"})
                        result = self._run_from(data, transcript)
                        return self._json(200, self._public_result(result))
                    if path == "/run":
                        data = self._read_form()
                        transcript_raw = data.get("transcript_file") or data.get("transcript") or ""
                        if isinstance(transcript_raw, bytes):
                            transcript_raw = transcript_raw.decode("utf-8", errors="replace")
                        if not str(transcript_raw).strip():
                            return self._html(400, _error_body("transcript_required", "A transcript is required."))
                        try:
                            result = self._run_from(data, transcript_raw)
                        except GateError as e:
                            return self._html(403, _error_body(e.code, e.message))
                        except (ValueError, KeyError) as e:
                            return self._html(400, _error_body("invalid_input", str(e)))
                        return self._html(200, _result_body(result))
                    if path in ("/api/stream", "/stream"):
                        return self._do_stream(path, parsed)
                    if path == "/api/notes":
                        data = self._read_json_body()
                        return self._do_notes(data)
                    if path == "/api/seal":
                        data = {}
                        try:
                            data = self._read_json_body()
                        except Exception:
                            data = {}
                        return self._do_seal(data)
                    if path in ("/api/verify", "/verify"):
                        return self._do_verify(path)
                    return self._respond(404)
                except GateError as e:
                    return self._gate_error(e)
                except (ValueError, KeyError) as e:
                    code = 400
                    payload = {"ok": False, "error": str(e), "notice": HONEST_NOTICE}
                    if path in ("/run", "/stream", "/verify"):
                        return self._html(code, _error_body("invalid_input", str(e)))
                    return self._json(code, payload)
                except Exception as e:  # noqa: BLE001
                    return self._json(500, {"ok": False, "error": str(e)})

            def _do_stream(self, path: str, parsed) -> None:
                ctype = self.headers.get("Content-Type") or ""
                session_id = None
                turns: List[Dict[str, Any]] = []
                errors: List[Dict[str, Any]] = []
                if "application/json" in ctype:
                    data = self._read_json_body()
                    session_id = str(data.get("session_id") or "").strip() or None
                    raw_turns = data.get("turns")
                    if raw_turns is not None:
                        turns = [_normalize_turn(t) for t in raw_turns] if isinstance(raw_turns, list) else []
                    elif data.get("ndjson"):
                        turns, errors = parse_ndjson_turns(str(data["ndjson"]))
                    else:
                        raise ValueError("stream requires 'turns' (list) or 'ndjson' (string)")
                    opts_data = data
                else:
                    raw = self._read_body()
                    text = raw.decode("utf-8", errors="replace")
                    if "ndjson=" in text or "session_id=" in text:
                        form = urllib.parse.parse_qs(text)
                        session_id = (form.get("session_id") or [""])[0].strip() or None
                        ndjson = (form.get("ndjson") or [""])[0]
                        turns, errors = parse_ndjson_turns(ndjson)
                        opts_data = {k: v[0] for k, v in form.items() if v}
                    else:
                        turns, errors = parse_ndjson_turns(text)
                        opts_data = {}
                session_id = session_id or f"stream-{uuid.uuid4().hex[:8]}"
                with outer._lock:
                    sess = outer._streams.setdefault(session_id, {"transcript": [], "seen_cue_ids": set()})
                    sess["transcript"].extend(turns)
                    transcript = list(sess["transcript"])
                    seen = set(sess["seen_cue_ids"])
                # Reuse the same pipeline over the accumulated transcript.
                opts = self._opts(opts_data)
                opts.pop("do_seal", None)
                result = run_pipeline(transcript, do_seal=False, **opts)
                new_cues = [c for c in result["cues"] if c["cue_id"] not in seen]
                with outer._lock:
                    sess["seen_cue_ids"].update(c["cue_id"] for c in new_cues)
                payload = {
                    "ok": True,
                    "notice": HONEST_NOTICE,
                    "session_id": session_id,
                    "turn_count": len(transcript),
                    "new_cue_count": len(new_cues),
                    "new_cues": new_cues,
                    "cue_count": len(result["cues"]),
                    "errors": errors,
                    "malformed_lines": len(errors),
                }
                if path == "/stream":
                    body = (
                        f"<div class='notice'><strong>{escape_html(NOTICE)}</strong></div>"
                        f"<div class='card'><h2>Stream result</h2>"
                        f"<p>Session: <code>{escape_html(session_id)}</code> · Turns so far: {len(transcript)} · "
                        f"New cues this batch: <strong>{len(new_cues)}</strong> · Malformed lines skipped: {len(errors)}</p>"
                    )
                    if errors:
                        body += "<h3>Malformed lines (skipped)</h3><ul>" + "".join(
                            f"<li>line {escape_html(e.get('line'))}: {escape_html(e.get('error'))}</li>"
                            for e in errors
                        ) + "</ul>"
                    body += "</div><div class='card'><h2>New cues</h2><table><thead><tr><th>Priority</th><th>Turn</th><th>Cue ID</th><th>Label</th><th>Score</th><th>Method / model</th><th>Message</th><th>Source</th></tr></thead><tbody>"
                    body += _cue_rows(new_cues)
                    body += "</tbody></table></div><p><a class='btn' href='/'>Back to Operate</a></p>"
                    return self._html(200, body)
                return self._json(200, payload)

            def _do_notes(self, data: Dict[str, Any]) -> None:
                last = outer._get_last()
                if last is None:
                    return self._json(404, {"ok": False, "error": "no_run_yet"})
                pkg = last.get("package") or {}
                notes = data.get("officer_cue_notes", data.get("notes"))
                if notes is None:
                    return self._json(400, {"ok": False, "error": "officer_cue_notes is required"})
                try:
                    updated = attach_officer_cue_notes(pkg, notes)
                except (ValueError, GateError) as e:
                    return self._json(409, {"ok": False, "error": str(e)})
                last["package"] = updated
                outer._store_last(last)
                return self._json(200, {"ok": True, "notice": HONEST_NOTICE,
                                        "officer_cue_notes": updated.get("officer_cue_notes")})

            def _do_seal(self, data: Dict[str, Any]) -> None:
                last = outer._get_last()
                if last is None:
                    return self._json(404, {"ok": False, "error": "no_run_yet"})
                pkg = last.get("package") or {}
                state = last.get("_gate_state")
                if state is None:
                    return self._json(409, {"ok": False, "error": "no gate state for last run"})
                if data.get("dual_control"):
                    for rec in data["dual_control"]:
                        record_dual_acknowledge(
                            state, str(rec.get("cue_id") or ""),
                            str(rec.get("first_officer_id") or rec.get("first_officer") or ""),
                            str(rec.get("second_officer_id") or rec.get("second_officer") or ""),
                            notes=str(rec.get("notes") or ""),
                        )
                hi_ids = last.get("high_priority_cue_ids") or []
                dual_ids = list(data.get("high_priority_cue_ids") or []) or (
                    hi_ids if state.mode == "government" else []
                )
                signer = None
                if data.get("sign"):
                    if load_signing_key() is None:
                        raise GateError("signing_key_missing",
                                        "Signing requires CUELIEZ_SIGNING_KEY or CUELIEZ_SIGNING_KEY_FILE.")
                    signer = hmac_signer()
                sealed_pkg = seal(pkg, state, high_priority_cue_ids=dual_ids, signer=signer)
                last["package"] = sealed_pkg
                last["sealed"] = True
                last["gate_state"] = state.to_dict()
                outer._store_last(last)
                return self._json(200, self._public_result(last))

            def _do_verify(self, path: str) -> None:
                ctype = self.headers.get("Content-Type") or ""
                if "application/json" in ctype:
                    data = self._read_json_body()
                    package = data.get("package", data)
                else:
                    form = self._read_form()
                    raw = form.get("package") or ""
                    try:
                        package = json.loads(raw)
                    except Exception as e:
                        if path == "/verify":
                            return self._html(400, _error_body("invalid_input", f"Package is not valid JSON: {e}"))
                        return self._json(400, {"ok": False, "error": f"invalid JSON: {e}"})
                result = verify_package(package)
                if path == "/verify":
                    status = "PASS" if result["ok"] else "FAIL"
                    cls = "ok" if result["ok"] else "bad"
                    body = (
                        f"<div class='notice'><strong>{escape_html(NOTICE)}</strong></div>"
                        f"<div class='card'><h2>Package verification: <span class='{cls}'>{status}</span></h2>"
                        f"<p>hash_ok: <strong>{escape_html(result['hash_ok'])}</strong></p>"
                        f"<p>Package hash: <code>{escape_html(result.get('package_hash') or '')}</code></p>"
                        f"<p>Signature: <code>{escape_html(json.dumps(result.get('signature'), default=str))}</code></p>"
                        f"<p><a class='btn' href='/'>Back to Operate</a></p></div>"
                    )
                    return self._html(200, body)
                return self._json(200, result)

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

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def __enter__(self) -> "WebFrontendServer":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()


__all__ = [
    "HONEST_NOTICE",
    "NOTICE",
    "WebFrontendServer",
    "parse_ndjson_turns",
    "parse_transcript_input",
    "run_pipeline",
    "verify_package",
]
