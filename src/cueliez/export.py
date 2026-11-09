"""Export surfaces for CueLiez packages.

Exports preserve observed-indicator framing, disclaimers, and gate/consent status.
They are designed for human review and downstream evidence/RMS attachment without
reinterpretation.
"""

from __future__ import annotations

import html
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .audit import audit_event
from .delivery.events import CueEvent, cues_from_observations
from .delivery.notes import OFFICER_CUE_NOTES_KEY, normalize_officer_cue_notes

EXPORT_NOTICE = (
    "This export contains observed indicators and interview-support cues only. "
    "It does not contain findings, diagnoses, or determinations about credibility."
)

_SAFE_BASENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
MAX_BASENAME_LEN = 120


def safe_export_basename(basename: str, default: str = "sealed_package") -> str:
    """Sanitize export basename to prevent path traversal and unsafe filenames."""
    name = Path(str(basename or "")).name  # drop any directory components
    name = name.replace("\x00", "").strip().strip(".")
    name = _SAFE_BASENAME_RE.sub("_", name)
    name = name[:MAX_BASENAME_LEN].strip("._")
    if not name or name in {".", ".."}:
        return default
    return name


def _resolve_under(root: Path, filename: str) -> Path:
    root = root.resolve()
    target = (root / filename).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Export path escapes output directory: {filename!r}")
    return target


def _write_export_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _display_value(value: Any) -> str:
    if value is None:
        return "not provided"
    if isinstance(value, list):
        return ", ".join(map(str, value)) if value else "not provided"
    return str(value)


def _gate_summary(package: Mapping[str, Any]) -> Dict[str, Any]:
    firewall = package.get("firewall") if isinstance(package.get("firewall"), Mapping) else {}
    annotations = package.get("annotations") if isinstance(package.get("annotations"), Mapping) else {}
    gate_state = package.get("gate_state") if isinstance(package.get("gate_state"), Mapping) else {}
    mode = gate_state.get("mode") or annotations.get("mode") or annotations.get("cue_pack_mode")
    dual_control_records = gate_state.get("dual_control_records")
    if dual_control_records is None:
        dual_control_records = package.get("dual_control_records") if "dual_control_records" in package else annotations.get("dual_control_records")
    intended_uses = gate_state.get("intended_uses")
    if intended_uses is None:
        intended_uses = package.get("intended_uses") if "intended_uses" in package else annotations.get("intended_uses")
    return {
        "mode": mode,
        "consent_rechecked": firewall.get("consent_rechecked") if "consent_rechecked" in firewall else None,
        "training_rechecked": firewall.get("training_rechecked") if "training_rechecked" in firewall else None,
        "consent": gate_state.get("consent"),
        "consent_attested_by": gate_state.get("consent_attested_by"),
        "training_acknowledged": gate_state.get("training_acknowledged"),
        "training_version": gate_state.get("training_version"),
        "dual_control_records": dual_control_records,
        "intended_uses": intended_uses,
        "gate_state_present": bool(gate_state),
    }


def export_package_json(package: Mapping[str, Any], path: str | Path) -> str:
    """Write canonical structured JSON export."""
    out = Path(path)
    safe_name = safe_export_basename(out.name, default="sealed_package.json")
    root = out.parent.resolve()
    root.mkdir(parents=True, exist_ok=True)
    out = _resolve_under(root, safe_name)
    payload = dict(package)
    payload.setdefault("export_notice", EXPORT_NOTICE)
    payload.setdefault("exported_at", time.time())
    _write_export_text(out, json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False, default=str) + "\n")
    return str(out)


def _cue_events(
    package: Mapping[str, Any],
    cues: Optional[Sequence[CueEvent | Mapping[str, Any]]],
    observations: Optional[Sequence[Mapping[str, Any]]],
    transcript: Optional[Sequence[Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    obs = list(observations) if observations is not None else list(package.get("observations") or [])
    if cues is None:
        return [c.to_dict() for c in cues_from_observations(obs, transcript=transcript)]
    return [c.to_dict() if isinstance(c, CueEvent) else dict(c) for c in cues]


def _format_source_quotes(quotes: Any) -> str:
    if not isinstance(quotes, list) or not quotes:
        return ""
    parts = []
    for q in quotes:
        if not isinstance(q, Mapping):
            continue
        ti = q.get("turn_index")
        role = f"{q.get('role')} " if q.get("role") else ""
        where = f"T{ti}" if ti is not None else "source"
        text = str(q.get("text") or "").replace("|", "\\|").replace("\n", " ")
        parts.append(f'{where} ({role}transcript): "{text}"')
    return " / ".join(parts)


def _high_priority_cue_ids(cue_events: Sequence[Mapping[str, Any]]) -> List[str]:
    return [str(c.get("cue_id")) for c in cue_events if c.get("priority") in {"high", "critical"} and c.get("cue_id")]


def render_package_summary_markdown(
    package: Mapping[str, Any],
    *,
    cues: Optional[Sequence[CueEvent | Mapping[str, Any]]] = None,
    observations: Optional[Sequence[Mapping[str, Any]]] = None,
    transcript: Optional[Sequence[Mapping[str, Any]]] = None,
) -> str:
    """Render a human-readable Markdown summary of a package."""
    pkg = dict(package)
    obs = list(observations) if observations is not None else list(pkg.get("observations") or [])
    cue_events = _cue_events(pkg, cues, observations, transcript=transcript)
    notes = normalize_officer_cue_notes(pkg.get(OFFICER_CUE_NOTES_KEY))
    gates = _gate_summary(pkg)
    hi_ids = _high_priority_cue_ids(cue_events)
    disclaimer = str(pkg.get("disclaimer") or "not provided")
    lines: List[str] = []
    lines.append("# CueLiez Package Summary")
    lines.append("")
    lines.append("## Disclaimer")
    lines.append("")
    lines.append(EXPORT_NOTICE)
    lines.append("")
    lines.append(f"**Disclaimer:** {disclaimer}")
    lines.append(f"**Package type:** {_display_value(pkg.get('epistemic_status'))} (observed indicators and cues only) — **Definitive finding:** {pkg.get('is_definitive_finding', False)}")
    lines.append("")
    lines.append("## Gate / Process Status")
    lines.append("")
    lines.append(f"- Mode/context: {_display_value(gates.get('mode'))}")
    lines.append(f"- Gate state: {'present' if gates.get('gate_state_present') else 'not provided'}")
    lines.append(f"- Consent rechecked at seal: {_display_value(gates.get('consent_rechecked'))}")
    lines.append(f"- Training rechecked at seal: {_display_value(gates.get('training_rechecked'))}")
    if gates.get("gate_state_present"):
        lines.append(f"- Consent recorded: {_display_value(gates.get('consent'))}")
        lines.append(f"- Consent attested by: {_display_value(gates.get('consent_attested_by'))}")
        lines.append(f"- Training acknowledged: {_display_value(gates.get('training_acknowledged'))}")
        lines.append(f"- Training version: {_display_value(gates.get('training_version'))}")
    dc = gates.get("dual_control_records")
    if dc is not None:
        lines.append(f"- Dual-control records present: {len(dc) if isinstance(dc, list) else 'yes'}")
    if gates.get("intended_uses") is not None:
        lines.append(f"- Intended uses: {_display_value(gates.get('intended_uses'))}")
    if hi_ids:
        lines.append(f"- High-priority cue IDs (dual-control workflow reference): {', '.join(hi_ids)}")
    lines.append("")
    lines.append("## System-Observed Cues (for human review)")
    lines.append("")
    if not cue_events:
        lines.append("No observation cues were present at export thresholds.")
    else:
        lines.append("| Priority | Turn | Cue ID | Label | Score | Method | Message | Source (transcript) |")
        lines.append("|---|---:|---|---|---:|---|---|---|")
        for c in cue_events:
            msg = str(c.get("message") or "").replace("|", "\\|").replace("\n", " ")
            turn = c.get("turn_index")
            src = _format_source_quotes(c.get("source_quotes"))
            method = str(c.get("method") or c.get("model_id") or "").replace("|", "\\|")
            lines.append(f"| {c.get('priority','')} | {turn if turn is not None else ''} | {c.get('cue_id','')} | {c.get('label','')} | {float(c.get('score') or 0):.2f} | {method} | {msg} | {src} |")
    if notes:
        lines.append("")
        lines.append("## Officer Notes (Human)")
        lines.append("")
        lines.append("Human-authored context recorded by the reviewing officer. These notes are not system findings.")
        lines.append("")
        for n in notes:
            lines.append(f"- **{n.get('cue_id')}** [{n.get('action','noted')}]"
                         + (f" (officer {n.get('officer_id')})" if n.get('officer_id') else "")
                         + f": {n.get('note') or '(no text)'}")
    lines.append("")
    lines.append("## Hash / Metadata")
    lines.append("")
    lines.append(f"- **Product:** {pkg.get('product', 'CueLiez')}")
    lines.append(f"- **Product version:** {_display_value(pkg.get('product_version'))}")
    lines.append(f"- **Schema version:** {_display_value(pkg.get('schema_version'))}")
    lines.append(f"- **Origin:** {_display_value(pkg.get('origin'))}")
    if pkg.get("session_id"):
        lines.append(f"- **Session ID:** {pkg.get('session_id')}")
    if pkg.get("seal_id"):
        lines.append(f"- **Seal ID:** {pkg.get('seal_id')}")
    lines.append(f"- **Sealed at (unix):** {_display_value(pkg.get('sealed_at'))}")
    lines.append(f"- **Package hash:** {_display_value(pkg.get('package_hash'))}")
    lines.append(f"- Observations in package: {len(obs)}")
    lines.append(f"- Cues rendered: {len(cue_events)}")
    lines.append(f"- Officer note records (human): {len(notes)}")
    lines.append("")
    lines.append("---")
    lines.append("Generated for review and evidence-system attachment without reinterpretation. Observed indicators and cues only; human judgment remains required.")
    return "\n".join(lines)


def render_package_summary_html(
    package: Mapping[str, Any],
    *,
    cues: Optional[Sequence[CueEvent | Mapping[str, Any]]] = None,
    observations: Optional[Sequence[Mapping[str, Any]]] = None,
    transcript: Optional[Sequence[Mapping[str, Any]]] = None,
    title: str = "CueLiez Package Summary",
) -> str:
    """Render a human-readable HTML summary (print/PDF-friendly)."""
    pkg = dict(package)
    obs = list(observations) if observations is not None else list(pkg.get("observations") or [])
    cue_events = _cue_events(pkg, cues, observations, transcript=transcript)
    notes = normalize_officer_cue_notes(pkg.get(OFFICER_CUE_NOTES_KEY))
    gates = _gate_summary(pkg)
    hi_ids = _high_priority_cue_ids(cue_events)
    disclaimer = html.escape(str(pkg.get("disclaimer") or "not provided"))
    notice = html.escape(EXPORT_NOTICE)
    rows = []
    for c in cue_events:
        prio = html.escape(str(c.get('priority','')))
        cls = " class='high-priority'" if c.get('priority') in {'high','critical'} else ""
        src = html.escape(_format_source_quotes(c.get('source_quotes')))
        method = html.escape(str(c.get('method') or c.get('model_id') or ''))
        rows.append(f"<tr{cls}>"
                    f"<td>{prio}</td>"
                    f"<td>{html.escape(str(c.get('turn_index','')))}</td>"
                    f"<td><code>{html.escape(str(c.get('cue_id','')))}</code></td>"
                    f"<td>{html.escape(str(c.get('label','')))}</td>"
                    f"<td>{float(c.get('score') or 0):.2f}</td>"
                    f"<td><code>{method}</code></td>"
                    f"<td>{html.escape(str(c.get('message','')))}</td>"
                    f"<td>{src}</td>"
                    "</tr>")
    cue_body = "\n".join(rows) or "<tr><td colspan='8'>No observation cues were present at export thresholds.</td></tr>"
    notes_section = ""
    if notes:
        note_items = "".join(
            f"<li><strong>{html.escape(str(n.get('cue_id')))}</strong> [{html.escape(str(n.get('action','noted')))}]"
            + (f" (officer {html.escape(str(n.get('officer_id')))})" if n.get('officer_id') else "")
            + f"]: {html.escape(str(n.get('note') or '(no text)'))}</li>" for n in notes
        )
        notes_section = f"<section><h2>Officer Notes (Human)</h2><p>Human-authored context recorded by the reviewing officer. These notes are not system findings.</p><ul>{note_items}</ul></section>"
    hi_line = f"<li>High-priority cue IDs (dual-control workflow reference): <code>{html.escape(', '.join(hi_ids))}</code></li>" if hi_ids else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; color: #111; }}
    .notice {{ background: #f6f7f9; border-left: 4px solid #555; padding: 12px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #fafafa; text-align: left; }}
    code {{ font-size: 12px; overflow-wrap: anywhere; }}
    .high-priority td:first-child {{ font-weight: 700; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <section>
    <h2>Disclaimer</h2>
    <div class="notice"><p><strong>Notice:</strong> {notice}</p><p><strong>Disclaimer:</strong> {disclaimer}</p></div>
    <p><strong>Package type:</strong> {html.escape(_display_value(pkg.get('epistemic_status')))} (observed indicators and cues only) &nbsp;|&nbsp; <strong>Definitive finding:</strong> {html.escape(str(pkg.get('is_definitive_finding', False)))}</p>
  </section>
  <section>
    <h2>Gate / Process Status</h2>
    <ul>
      <li>Mode/context: {html.escape(_display_value(gates.get('mode')))}</li>
      <li>Gate state: {html.escape('present' if gates.get('gate_state_present') else 'not provided')}</li>
      <li>Consent rechecked at seal: {html.escape(_display_value(gates.get('consent_rechecked')))}</li>
      <li>Training rechecked at seal: {html.escape(_display_value(gates.get('training_rechecked')))}</li>
      {hi_line}
    </ul>
  </section>
  <section>
    <h2>System-Observed Cues (for human review)</h2>
    <table><thead><tr><th>Priority</th><th>Turn</th><th>Cue ID</th><th>Label</th><th>Score</th><th>Method/Model</th><th>Message</th><th>Source (transcript)</th></tr></thead><tbody>{cue_body}</tbody></table>
  </section>
  {notes_section}
  <section>
    <h2>Hash / Metadata</h2>
    <ul>
      <li><strong>Product:</strong> {html.escape(str(pkg.get('product','CueLiez')))}</li>
      <li><strong>Product version:</strong> <code>{html.escape(_display_value(pkg.get('product_version')))}</code></li>
      <li><strong>Schema version:</strong> <code>{html.escape(_display_value(pkg.get('schema_version')))}</code></li>
      <li><strong>Package hash:</strong> <code>{html.escape(_display_value(pkg.get('package_hash')))}</code></li>
      <li><strong>Sealed at (unix):</strong> {html.escape(_display_value(pkg.get('sealed_at')))}</li>
      <li>Observations in package: {len(obs)} | Cues rendered: {len(cue_events)} | Officer note records (human): {len(notes)}</li>
    </ul>
  </section>
  <hr/>
  <p>Generated for review and evidence-system attachment without reinterpretation. Observed indicators and cues only; human judgment remains required.</p>
</body>
</html>"""


def export_sealed_package(
    package: Mapping[str, Any],
    out_dir: str | Path,
    *,
    basename: str = "sealed_package",
    formats: Sequence[str] = ("json", "md", "html"),
    cues: Optional[Sequence[CueEvent | Mapping[str, Any]]] = None,
    observations: Optional[Sequence[Mapping[str, Any]]] = None,
    transcript: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, str]:
    """Export a package to requested formats. Returns paths by format."""
    root = Path(out_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    safe_base = safe_export_basename(basename)
    paths: Dict[str, str] = {}
    if "json" in formats:
        paths["json"] = export_package_json(package, root / f"{safe_base}.json")
    if "md" in formats or "markdown" in formats:
        p = _resolve_under(root, f"{safe_base}.summary.md")
        _write_export_text(p, render_package_summary_markdown(package, cues=cues, observations=observations, transcript=transcript) + "\n")
        paths["md"] = str(p)
    if "html" in formats:
        p = _resolve_under(root, f"{safe_base}.summary.html")
        _write_export_text(p, render_package_summary_html(package, cues=cues, observations=observations, transcript=transcript) + "\n")
        paths["html"] = str(p)
    audit_event("export.package", details={"formats": sorted(paths.keys()), "basename": safe_base, "file_count": len(paths)})
    return paths
