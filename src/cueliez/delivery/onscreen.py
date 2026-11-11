"""Onscreen cue rendering for professionals.

Produces human-readable and structured display payloads. All rendered text must
remain non-verdict and cue-oriented.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .events import CueEvent, cues_from_observations
from .notes import notes_by_cue_id
from .safe import csp_policy_for, escape_html as _esc, json_for_script, visible_text

_PRIORITY_ICON = {"low": "·", "medium": "▲", "high": "◆", "critical": "●"}
_ANSI = {
    "reset": "\x1b[0m",
    "bold": "\x1b[1m",
    "dim": "\x1b[2m",
    "low": "\x1b[36m",
    "medium": "\x1b[33m",
    "high": "\x1b[35m",
    "critical": "\x1b[31m",
}


class OnscreenCueRenderer:
    """Render cue events to onscreen formats."""

    def __init__(self, *, use_color: bool = False, show_evidence: bool = False):
        self.use_color = use_color
        self.show_evidence = show_evidence

    def render_text(self, cues: Sequence[CueEvent], *, header: Optional[str] = None) -> str:
        lines: List[str] = []
        if header:
            lines.append(visible_text(header))
        if not cues:
            lines.append("No observation cues at current thresholds.")
            return "\n".join(lines)
        lines.append(f"Observation cues: {len(cues)} (review required; not findings)")
        for c in cues:
            icon = _PRIORITY_ICON.get(c.priority, "·")
            prefix = f"{icon} {c.priority.upper():8} "
            if self.use_color:
                color = _ANSI.get(c.priority, "")
                prefix = f"{color}{_ANSI['bold']}{prefix}{_ANSI['reset']}"
            turn = f"T{c.turn_index} " if c.turn_index is not None else ""
            line = f"{prefix}{turn}{visible_text(c.message)} (score={c.score:.2f}, {visible_text(c.category)}, id={visible_text(c.cue_id)}, method={visible_text(c.method)})"
            lines.append(line)
            if self.show_evidence and c.evidence_summary:
                ev = visible_text(json.dumps(c.evidence_summary, ensure_ascii=False))
                dim = _ANSI["dim"] if self.use_color else ""
                rst = _ANSI["reset"] if self.use_color else ""
                lines.append(f"           {dim}evidence: {ev}{rst}")
            for q in getattr(c, "source_quotes", []) or []:
                ti = q.get("turn_index")
                role = f"{visible_text(q.get('role'))} " if q.get("role") else ""
                where = f"T{visible_text(ti)}" if ti is not None else "source"
                lines.append(f"           Source ({where}, {role}transcript): \"{visible_text(q.get('text',''))}\"")
        lines.append("Notice: cues are probabilistic observations for professional judgment, not determinations.")
        return "\n".join(lines)

    def render_panel(
        self,
        observations: Sequence[Mapping[str, Any]],
        *,
        officer_cue_notes: Optional[Sequence[Mapping[str, Any]]] = None,
        transcript: Optional[Sequence[Mapping[str, Any]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        cue_kwargs = {k: v for k, v in kwargs.items() if k in ("min_score", "max_cues")}
        cues = cues_from_observations(observations, transcript=transcript, **cue_kwargs)
        counts: Dict[str, int] = {}
        for c in cues:
            counts[c.priority] = counts.get(c.priority, 0) + 1
        note_index = notes_by_cue_id(officer_cue_notes)
        cue_payloads = []
        for c in cues:
            d = c.to_dict()
            d["officer_actions"] = ["acknowledged", "dismissed", "noted"]
            d["officer_notes"] = note_index.get(c.cue_id, [])
            d["display"] = {
                "turn_link": f"turn:{c.turn_index}" if c.turn_index is not None else None,
                "glanceable": True,
            }
            cue_payloads.append(d)
        return {
            "type": "cueliez_onscreen_cues",
            "surface": "officer_only",
            "subject_visible_by_default": False,
            "generated_at": time.time(),
            "cue_count": len(cues),
            "priority_counts": counts,
            "cues": cue_payloads,
            "text": self.render_text(cues, header=kwargs.get("header")),
            "notice": "Observation cues for professional review; not findings. Officer surface; not shown to subject by default.",
        }

    def render_html(self, cues: Sequence[CueEvent], *, title: str = "CueLiez Observation Cues") -> str:
        rows = []
        for c in cues:
            ev = _esc(json.dumps(c.evidence_summary, ensure_ascii=False)) if c.evidence_summary else ""
            quotes = []
            for q in getattr(c, "source_quotes", []) or []:
                ti = q.get("turn_index")
                role = f"{q.get('role')} " if q.get("role") else ""
                where = f"T{ti}" if ti is not None else "source"
                quotes.append(f"<div class='source'><strong>Source ({_esc(where)}, {_esc(role)}transcript):</strong> “{_esc(str(q.get('text','')))}”</div>")
            cue_cell = _esc(c.message) + ("".join(quotes) if quotes else "")
            rows.append(
                "<tr>"
                f"<td class='p {_esc(c.priority)}'>{_esc(c.priority.upper())}</td>"
                f"<td>{_esc(str(c.turn_index) if c.turn_index is not None else '—')}</td>"
                f"<td>{_esc(c.category)}</td>"
                f"<td>{cue_cell}</td>"
                f"<td>{c.score:.2f}</td>"
                f"<td><code>{_esc(c.method)}</code></td>"
                f"<td><code>{ev}</code></td>"
                "</tr>"
            )
        body = "\n".join(rows) or "<tr><td colspan='7'>No observation cues at current thresholds.</td></tr>"
        return (
            "<section class='cueliez-cues'>"
            f"<h2>{_esc(title)}</h2>"
            "<p class='notice'>Observation cues for professional review; not findings.</p>"
            "<table><thead><tr><th>Priority</th><th>Turn</th><th>Category</th><th>Cue / Source transcript</th><th>Score</th><th>Method/Model</th><th>Evidence</th></tr></thead>"
            f"<tbody>{body}</tbody></table></section>"
        )

    def render_officer_html(
        self,
        observations: Sequence[Mapping[str, Any]],
        *,
        transcript: Optional[Sequence[Mapping[str, Any]]] = None,
        title: str = "CueLiez Officer Cues",
        min_score: float = 0.0,
        max_cues: Optional[int] = None,
    ) -> str:
        """Render a low-distraction officer surface (tablet/secondary display).

        Supports acknowledge/dismiss/note locally and exports officer action JSON
        for attachment to a sealed package. Subject is not shown this stream by default.
        """
        cues = cues_from_observations(observations, transcript=transcript, min_score=min_score, max_cues=max_cues)
        cards = []
        for c in cues:
            turn = _esc(str(c.turn_index)) if c.turn_index is not None else "—"
            msg = _esc(c.message)
            quotes = []
            for q in getattr(c, "source_quotes", []) or []:
                ti = q.get("turn_index")
                role = f"{q.get('role')} " if q.get("role") else ""
                where = f"T{ti}" if ti is not None else "source"
                quotes.append(f"<div class='source'><strong>Source ({_esc(where)}, {_esc(role)}transcript):</strong> “{_esc(str(q.get('text','')))}”</div>")
            source_html = "".join(quotes)
            cards.append(
                f"<article class='cue {_esc(c.priority)}' data-cue-id='{_esc(c.cue_id)}' data-priority='{_esc(c.priority)}' data-label='{_esc(c.label)}' data-turn='{turn}'>"
                f"<div class='meta'><span class='prio'>{_esc(c.priority.upper())}</span> <span class='turn'>Turn {turn}</span> <span class='score'>score {c.score:.2f}</span> <span class='method'>{_esc(c.method)}</span></div>"
                f"<div class='msg'>{msg}</div>"
                f"{source_html}"
                f"<div class='id'><code>{_esc(c.cue_id)}</code></div>"
                "<div class='actions'>"
                "<button data-action='acknowledged'>Acknowledge</button>"
                "<button data-action='dismissed'>Dismiss</button>"
                "<button data-action='noted'>Add note</button>"
                "</div>"
                "<textarea placeholder='Optional officer note (observation context only)' rows='2'></textarea>"
                "<div class='state'></div>"
                "</article>"
            )
        body = "\n".join(cards) or "<p class='empty'>No observation cues at current thresholds.</p>"
        cues_json = json_for_script([c.to_dict() for c in cues])
        page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta http-equiv="Content-Security-Policy" content="__CSP__">
  <title>{_esc(title)}</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ font-family: system-ui, sans-serif; margin: 12px; background: #111; color: #eee; }}
    header {{ position: sticky; top: 0; background: #111; padding: 8px 0; border-bottom: 1px solid #333; }}
    h1 {{ font-size: 18px; margin: 0 0 4px; }}
    .notice {{ font-size: 12px; color: #bbb; margin: 0; }}
    .toolbar button {{ margin-right: 8px; }}
    .cue {{ border: 1px solid #333; border-left: 6px solid #666; border-radius: 8px; padding: 10px; margin: 10px 0; background: #1a1a1a; }}
    .cue.low {{ border-left-color: #4aa3df; }} .cue.medium {{ border-left-color: #d4a017; }}
    .cue.high {{ border-left-color: #b57edc; }} .cue.critical {{ border-left-color: #e05d5d; }}
    .meta {{ font-size: 12px; color: #bbb; display: flex; gap: 10px; }}
    .msg {{ font-size: 18px; margin: 8px 0; line-height: 1.3; }}
    .source {{ font-size: 13px; color: #ccc; margin: 6px 0; padding: 6px 8px; background: #141414; border-left: 3px solid #555; }}
    .id {{ font-size: 11px; color: #888; }}
    .actions button {{ margin-right: 6px; margin-top: 6px; }}
    textarea {{ width: 100%; box-sizing: border-box; margin-top: 8px; background: #0f0f0f; color: #eee; border: 1px solid #333; border-radius: 6px; padding: 8px; }}
    .state {{ font-size: 12px; color: #8fd694; min-height: 16px; margin-top: 4px; }}
    .empty {{ color: #bbb; }}
    pre {{ white-space: pre-wrap; font-size: 12px; background: #0f0f0f; padding: 8px; border-radius: 6px; }}
  </style>
</head>
<body>
  <header>
    <h1>{_esc(title)}</h1>
    <p class="notice"><strong>Officer-only view.</strong> Subject is not shown this stream by default. Observation cues for professional review only; not findings, diagnoses, or determinations.</p>
    <p class="notice">Officer surface (not shown to subject by default). Observation cues for professional review; not findings.</p>
    <div class="toolbar">
      <button id="export-notes" type="button">Copy officer actions JSON</button>
      <button id="download-notes" type="button">Download officer actions JSON</button>
    </div>
  </header>
  <main id="cues">{body}</main>
  <h2>Officer actions JSON</h2>
  <pre id="notes-json">[]</pre>
  <script id="cue-data" type="application/json">{cues_json}</script>
  <script>
    const notes = {{}};
    function renderNotes() {{
      const arr = Object.values(notes);
      document.getElementById('notes-json').textContent = JSON.stringify(arr, null, 2);
      return arr;
    }}
    document.querySelectorAll('.cue').forEach(card => {{
      card.querySelectorAll('button[data-action]').forEach(btn => {{
        btn.addEventListener('click', () => {{
          const cueId = card.dataset.cueId;
          const action = btn.dataset.action;
          const note = card.querySelector('textarea').value || '';
          notes[cueId] = {{
            cue_id: cueId, action, note, priority: card.dataset.priority,
            label: card.dataset.label, turn_index: card.dataset.turn === '—' ? null : Number(card.dataset.turn),
            recorded_at: Date.now()/1000
          }};
          card.querySelector('.state').textContent = action + (note ? ' (note saved locally)' : '');
          renderNotes();
        }});
      }});
    }});
    document.getElementById('export-notes').addEventListener('click', async () => {{
      try {{ await navigator.clipboard.writeText(JSON.stringify(renderNotes(), null, 2)); }} catch (e) {{}}
    }});
    document.getElementById('download-notes').addEventListener('click', () => {{
      const blob = new Blob([JSON.stringify(renderNotes(), null, 2)], {{type: 'application/json'}});
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'officer_cue_notes.json'; a.click();
    }});
    renderNotes();
  </script>
</body>
</html>"""
        return page.replace("__CSP__", csp_policy_for(page), 1)
