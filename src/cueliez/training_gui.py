"""Web-based training GUI for CueLiez (not CLI training).

Provides a local browser UI for: module browsing/viewing (with optional local
media: images/screenshots/video), interactive scored quizzes, self-training
sandbox/playground (observation cues on sample or pasted transcripts), and
minimal credential record workflows. Observation/cue-only; no verdicts.
"""

from __future__ import annotations

import html
import json
import mimetypes
import threading
import time
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

from .audit import audit_event
from .compliance.records import TrainingRecordStore
from .compliance.training import (
    TrainingAcknowledgement,
    domain_training,
    get_training_bundle,
    validate_training_ack,
)
from .delivery.events import cues_from_observations
from .observations import default_runner

DEFAULT_MEDIA_DIR = Path(__file__).resolve().parents[2] / "docs" / "training" / "media"


def _quizzes() -> Dict[str, List[Dict[str, Any]]]:
    # Real, domain-aligned interactive quiz content (observation/cue-only).
    common = [
        {"id": "c1", "q": "What does CueLiez produce for human review?", "choices": ["Deception verdicts", "Observation cues/indicators", "Guilt findings", "Clinical diagnoses"], "answer": 1,
         "explain": "CueLiez produces observation cues/indicators for human review, not verdicts or diagnoses."},
        {"id": "c2", "q": "Who makes final judgments and decisions?", "choices": ["The system automatically", "Only the model", "The human operator/professional", "The dashboard"], "answer": 2,
         "explain": "Human judgment remains required; the system supports inquiry with cues."},
        {"id": "c3", "q": "Which claim is prohibited?", "choices": ["A cue suggests a possible inconsistency", "The system outputs a prohibited definitive finding about truthfulness", "An indicator is probabilistic", "A follow-up question may clarify"], "answer": 1,
         "explain": "Definitive truthfulness/guilt findings are prohibited; CueLiez provides observation cues only."},
    ]
    gov = common + [
        {"id": "g1", "q": "In government mode, what may be required before sealing high-priority cues?", "choices": ["Nothing", "Dual-control", "Automatic clearance", "Diagnosis"], "answer": 1,
         "explain": "Government/high-stakes workflows may require dual-control and gate discipline."},
    ]
    leg = common + [
        {"id": "l1", "q": "How should a cue be used in a legal interview?", "choices": ["As proof of guilt", "To guide a neutral clarifying question", "As a detention decision", "As a numerical credibility verdict"], "answer": 1,
         "explain": "Cues guide human-led clarification; they are not legal findings."},
    ]
    med = common + [
        {"id": "m1", "q": "In clinical/support contexts, CueLiez cues are:", "choices": ["Diagnoses", "Non-diagnostic communication/history-taking support", "Treatment decisions", "Credibility determinations"], "answer": 1,
         "explain": "Clinical-context use is non-diagnostic and human-led."},
    ]
    thrp = common + [
        {"id": "t1", "q": "In therapy/support contexts, a cue should prompt:", "choices": ["Adversarial accusation", "Supportive clarification and pacing", "Automated care decisions", "Risk adjudication"], "answer": 1,
         "explain": "Use cues for supportive, human-led clarification and pacing."},
    ]
    return {"gov": gov, "leg": leg, "med": med, "thrp": thrp}


def _score_quiz(domain: str, answers: Dict[str, int]) -> Dict[str, Any]:
    qs = _quizzes().get(domain) or []
    results = []
    correct = 0
    for q in qs:
        chosen = answers.get(q["id"])
        ok = chosen == q["answer"]
        if ok:
            correct += 1
        results.append({"id": q["id"], "ok": ok, "chosen": chosen, "answer": q["answer"], "explain": q["explain"]})
    total = len(qs)
    score = (correct / total) if total else 0.0
    passed = score >= 0.75 and total > 0
    return {"domain": domain, "correct": correct, "total": total, "score": score, "passed": passed, "results": results}


def _media_items(domain: str, media_dir: Path) -> List[Dict[str, Any]]:
    items = []
    base = Path(media_dir)
    candidates = [
        ("image", base / domain / "overview.png", "Module overview (image/screenshot)"),
        ("image", base / domain / "workflow.png", "Workflow screenshot"),
        ("video", base / domain / "intro.mp4", "Intro video"),
        ("video", base / domain / "intro.webm", "Intro video (webm)"),
    ]
    for kind, path, title in candidates:
        items.append({"kind": kind, "title": title, "path": str(path.relative_to(base.parent)) if base.parent in path.parents or path == base else path.name, "exists": path.exists()})
    return items


def _html_page(title: str, body: str) -> bytes:
    doc = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{html.escape(title)}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#0b1020;color:#e8eefc}} a{{color:#8fd3ff}}
header{{padding:16px 20px;background:#121a33;border-bottom:1px solid #26325f}} main{{padding:20px;max-width:1100px;margin:0 auto}}
.card{{background:#121a33;border:1px solid #26325f;border-radius:12px;padding:14px;margin:12px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}}
.btn{{display:inline-block;padding:8px 12px;border-radius:8px;background:#234; border:1px solid #456;color:#e8eefc;text-decoration:none;cursor:pointer}}
.btn.primary{{background:#1f5eff;border-color:#4c7dff}}
.muted{{color:#a8b4d8}} .ok{{color:#7dffb3}} .bad{{color:#ff8f8f}}
textarea,input,select{{width:100%;box-sizing:border-box;padding:8px;border-radius:8px;border:1px solid #456;background:#091022;color:#e8eefc}}
pre{{white-space:pre-wrap;background:#091022;padding:10px;border-radius:8px;border:1px solid #26325f}}
table{{width:100%;border-collapse:collapse}} th,td{{border:1px solid #26325f;padding:8px;vertical-align:top}}
.media-missing{{padding:10px;border:1px dashed #456;border-radius:8px;color:#a8b4d8}}
img,video{{max-width:100%;border-radius:8px;border:1px solid #26325f}}
nav a{{margin-right:10px}}
</style></head><body>
<header><strong>CueLiez Training Portal (GUI)</strong> <span class='muted'>— observation/cue training only; not a lie detector; not CLI training.</span>
<nav><a href='/'>Home</a><a href='/sandbox'>Self-Training Sandbox</a><a href='/records'>Credentials/Records</a></nav></header>
<main>{body}</main></body></html>"""
    return doc.encode("utf-8")


class TrainingGUIServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 911, *, media_dir: Optional[Path] = None, records_path: Optional[Path] = None):
        self.host = host
        self.port = port
        self.media_dir = Path(media_dir) if media_dir else DEFAULT_MEDIA_DIR
        self.records = TrainingRecordStore(records_path or Path("cueliez_training_records.jsonl"))
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._server:
            return
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # noqa
                return

            def _send(self, code: int, body: bytes, content_type: str = "text/html; charset=utf-8") -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _json(self, obj: Any, code: int = 200) -> None:
                self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"), "application/json; charset=utf-8")

            def _read_json(self) -> Dict[str, Any]:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b"{}"
                try:
                    d = json.loads(raw.decode("utf-8"))
                    return d if isinstance(d, dict) else {}
                except Exception:
                    return {}

            def do_GET(self):  # noqa
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                if path == "/":
                    mods = get_training_bundle()
                    cards = "".join(
                        f"<div class='card'><h3>{html.escape(m.title)}</h3><p class='muted'>Domain: {html.escape(m.domain)} | Mode: {html.escape(m.mode)} | v{html.escape(m.version)}</p>"
                        f"<a class='btn primary' href='/module/{html.escape(m.domain)}'>Open module</a> <a class='btn' href='/quiz/{html.escape(m.domain)}'>Interactive quiz</a></div>"
                        for m in mods
                    )
                    body = f"<div class='card'><p>This GUI provides full training workflows (modules, media, interactive quizzes, sandbox, records). It remains <strong>observation/cue-only</strong> and never produces verdicts or diagnoses.</p></div><div class='grid'>{cards}</div>"
                    return self._send(200, _html_page("CueLiez Training", body))
                if path.startswith("/module/"):
                    domain = path.rsplit("/", 1)[-1]
                    try:
                        m = domain_training(domain)
                    except Exception:
                        return self._send(404, _html_page("Not found", "<p>Module not found.</p>"))
                    media = _media_items(domain, outer.media_dir)
                    media_html = []
                    for it in media:
                        fpath = outer.media_dir.parent / it["path"] if not Path(it["path"]).is_absolute() else Path(it["path"])
                        if it["exists"] and fpath.exists():
                            url = "/media/" + urllib.parse.quote(str(fpath.relative_to(outer.media_dir)).replace('\\','/'))
                            if it["kind"] == "image":
                                media_html.append(f"<div class='card'><strong>{html.escape(it['title'])}</strong><div><img src='{html.escape(url)}' alt='{html.escape(it['title'])}'></div></div>")
                            else:
                                media_html.append(f"<div class='card'><strong>{html.escape(it['title'])}</strong><div><video controls src='{html.escape(url)}'></video></div></div>")
                        else:
                            media_html.append(f"<div class='card'><strong>{html.escape(it['title'])}</strong><div class='media-missing'>No media file provided yet. Add a file under <code>{html.escape(str(outer.media_dir / domain))}</code> to display it here.</div></div>")
                    def sec(name, items):
                        return f"<h3>{html.escape(name)}</h3><ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in items) + "</ul>"
                    body = (
                        f"<div class='card'><h2>{html.escape(m.title)}</h2><p class='muted'>ID: {html.escape(m.id)} | v{html.escape(m.version)} | mode: {html.escape(m.mode)}</p></div>"
                        + "".join(media_html)
                        + f"<div class='card'>{sec('Objectives', m.objectives)}{sec('Required topics', m.required_topics)}{sec('Operator responsibilities', m.operator_responsibilities)}{sec('Prohibited uses (review)', m.prohibited_uses_review)}{sec('Assessment checks', m.assessment_checks)}</div>"
                        + f"<div class='card'><a class='btn primary' href='/quiz/{html.escape(domain)}'>Take interactive quiz</a> <a class='btn' href='/sandbox?domain={html.escape(domain)}'>Open sandbox</a></div>"
                    )
                    return self._send(200, _html_page(m.title, body))
                if path.startswith("/quiz/"):
                    domain = path.rsplit("/", 1)[-1]
                    qs = _quizzes().get(domain)
                    if not qs:
                        return self._send(404, _html_page("Not found", "<p>Quiz not found.</p>"))
                    blocks = []
                    for q in qs:
                        opts = "".join(f"<label><input type='radio' name='{html.escape(q['id'])}' value='{i}'> {html.escape(c)}</label><br>" for i,c in enumerate(q['choices']))
                        blocks.append(f"<div class='card'><p><strong>{html.escape(q['q'])}</strong></p>{opts}</div>")
                    body = f"<h2>Interactive Quiz — {html.escape(domain.upper())}</h2><p class='muted'>Score is computed server-side. Passing is for training workflow support (>=75%); not a legal/clinical/deception-detection certification.</p><form id='f'>{''.join(blocks)}<div class='card'><label>Operator ID</label><input name='operator_id' required><label>Actor/Trainer ID (optional)</label><input name='actor'><button class='btn primary' type='submit'>Submit quiz</button></div></form><div id='out'></div><script>document.getElementById('f').onsubmit=async(e)=>{{e.preventDefault();const fd=new FormData(e.target);const answers={{}};for(const [k,v] of fd.entries()){{if(k!=='operator_id'&&k!=='actor') answers[k]=Number(v);}} const res=await fetch('/api/quiz/{html.escape(domain)}/submit',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{operator_id:fd.get('operator_id'),actor:fd.get('actor'),answers}})}});const j=await res.json();document.getElementById('out').innerHTML='<div class=\"card\"><pre>'+JSON.stringify(j,null,2)+'</pre></div>';}}</script>"
                    return self._send(200, _html_page(f"Quiz {domain}", body))
                if path == "/sandbox":
                    body = """<h2>Self-Training Sandbox / Playground</h2>
<div class='card'><p class='muted'>Paste a transcript JSON array (role/text turns) or use a sample. The sandbox runs observation cues for learning purposes only — <strong>observation/cue-only, no verdicts</strong>.</p>
<label>Transcript JSON</label><textarea id='t' rows='12'>[
  {"role":"interviewer","text":"Can you walk me through your evening?"},
  {"role":"subject","text":"I think I was home around maybe nine, I don't really recall exactly."},
  {"role":"interviewer","text":"Who was with you?"},
  {"role":"subject","text":"No one. I mean, I was alone."}
]</textarea>
<button class='btn primary' onclick='run()'>Run observation cues</button></div>
<div id='out'></div>
<script>async function run(){const res=await fetch('/api/sandbox/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({transcript:document.getElementById('t').value})});document.getElementById('out').innerHTML='<div class="card"><pre>'+JSON.stringify(await res.json(),null,2)+'</pre></div>';}</script>"""
                    return self._send(200, _html_page("Sandbox", body))
                if path == "/records":
                    body = """<h2>Credentials / Records (minimal technical support)</h2>
<div class='card'><label>Credential ID</label><input id='cid'><button class='btn' onclick='verify()'>Verify</button></div>
<div id='out'></div>
<script>async function verify(){const id=document.getElementById('cid').value;const res=await fetch('/api/records/verify?id='+encodeURIComponent(id));document.getElementById('out').innerHTML='<div class="card"><pre>'+JSON.stringify(await res.json(),null,2)+'</pre></div>';}</script>
<p class='muted'>Issuance via GUI/API uses the minimal record store; configure RBAC env vars for enforced admin controls. Not a full LMS/cert authority.</p>"""
                    return self._send(200, _html_page("Records", body))
                if path.startswith("/media/"):
                    rel = urllib.parse.unquote(path[len("/media/"):])
                    target = (outer.media_dir / rel).resolve()
                    root = outer.media_dir.resolve()
                    if root not in target.parents and target != root or not target.exists() or not target.is_file():
                        return self._send(404, b"not found", "text/plain")
                    ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                    return self._send(200, target.read_bytes(), ctype)
                if path.startswith("/api/modules"):
                    return self._json([m.to_dict() for m in get_training_bundle()])
                return self._send(404, b"not found", "text/plain")

            def do_POST(self):  # noqa
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                data = self._read_json()
                if path.startswith("/api/quiz/") and path.endswith("/submit"):
                    domain = path.split("/")[3]
                    try:
                        mod = domain_training(domain)
                    except Exception:
                        return self._json({"ok": False, "error": "unknown_domain"}, 400)
                    score = _score_quiz(domain, data.get("answers") or {})
                    ack = TrainingAcknowledgement(
                        module_id=mod.id, module_version=mod.version,
                        operator_id=str(data.get("operator_id") or "").strip(),
                        completed_topics=list(mod.required_topics) if score["passed"] else [],
                        assessment_passed=bool(score["passed"]),
                        acknowledged_at=time.time(),
                        notes=f"gui-quiz score={score['score']:.2f}",
                    )
                    validation = validate_training_ack(mod, ack)
                    issued = None
                    if validation.get("valid"):
                        try:
                            rec = outer.records.issue(mod, ack, actor=str(data.get("actor") or data.get("operator_id") or "").strip() or None)
                            issued = {"credential_id": rec.credential_id, "status": rec.status, "expires_at": rec.expires_at}
                        except Exception as e:
                            issued = {"error": str(e)}
                    audit_event("training.quiz_submit", details={"domain": domain, "passed": score["passed"], "score": score["score"]})
                    return self._json({"ok": True, "score": score, "ack_valid": validation, "credential": issued})
                if path == "/api/sandbox/run":
                    raw = data.get("transcript")
                    if isinstance(raw, str):
                        try:
                            transcript = json.loads(raw)
                        except Exception:
                            return self._json({"ok": False, "error": "invalid_json"}, 400)
                    else:
                        transcript = raw
                    if not isinstance(transcript, list):
                        return self._json({"ok": False, "error": "transcript_must_be_list"}, 400)
                    observations = default_runner().run(transcript)
                    cues = [c.to_dict() for c in cues_from_observations(observations, transcript=transcript)]
                    return self._json({"ok": True, "notice": "Observation/cue-only sandbox output for self-training. No verdicts.", "observation_count": len(observations), "cue_count": len(cues), "cues": cues, "observations": observations[:50]})
                return self._json({"ok": False, "error": "not_found"}, 404)

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        audit_event("training.gui_start", details={"host": self.host, "port": self.port})

    def stop(self) -> None:
        if self._server:
            self._server.shutdown(); self._server.server_close(); self._server = None
        if self._thread:
            self._thread.join(timeout=5); self._thread = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def __enter__(self):
        self.start(); return self

    def __exit__(self, *exc):
        self.stop()
