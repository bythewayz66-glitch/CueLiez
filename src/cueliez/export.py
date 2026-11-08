"""Export surfaces for sealed CueLiez packages.

Exports preserve observed-indicator framing, disclaimers, and gate/consent status.
They are designed for human review and downstream evidence/RMS attachment without
reinterpretation.
"""

from __future__ import annotations

import html
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .delivery.events import CueEvent, cues_from_observations
from .delivery.notes import OFFICER_CUE_NOTES_KEY, normalize_officer_cue_notes

EXPORT_NOTICE = (
    "This export contains observed indicators and interview-support cues only. "
    "It does not contain findings, diagnoses, or determinations about credibility."
)


def _gate_summary(package: Mapping[str, Any]) -> Dict[str, Any]:
    firewall = package.get("firewall") if isinstance(package.get("firewall"), Mapping) else {}
    # Some gate state may be carried under annotations or explicit fields by callers.
    annotations = package.get("annotations") if isinstance(package.get("annotations"), Mapping) else {}
    return {
        "mode": annotations.get("mode") or annotations.get("cue_pack_mode"),
        "consent_rechecked": firewall.get("consent_rechecked"),
        "training_rechecked": firewall.get("training_rechecked"),
        "dual_control_records": package.get("dual_control_records") if "dual_control_records" in package else annotations.get("dual_control_records"),
        "intended_uses": package.get("intended_uses") if "intended_uses" in package else annotations.get("intended_uses"),
    }


def export_package_json(package: Mapping[str, Any], path: str | Path) -> str:
    """Write canonical structured JSON export."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(package)
    payload.setdefault("export_notice", EXPORT_NOTICE)
    payload.setdefault("exported_at", time.time())
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
    return str(out)


def render_package_summary_markdown(
    package: Mapping[str, Any],
    *,
    cues: Optional[Sequence[CueEvent | Mapping[str, Any]]] = None,
    observations: Optional[Sequence[Mapping[str, Any]]] = None,
) -> str:
    """Render a human-readable Markdown summary of a sealed package."""
    pkg = dict(package)
    obs = list(observations) if observations is not None else list(pkg.get("observations") or [])
    cue_events: List[Dict[str, Any]]
    if cues is None:
        cue_events = [c.to_dict() for c in cues_from_observations(obs)]
    else:
        cue_events = [c.to_dict() if isinstance(c, CueEvent) else dict(c) for c in cues]
    notes = normalize_officer_cue_notes(pkg.get(OFFICER_CUE_NOTES_KEY))
    gates = _gate_summary(pkg)
    disclaimer = str(pkg.get("disclaimer") or "")
    lines: List[str] = []
    lines.append("# CueLiez Sealed Package Summary")
    lines.append("")
    lines.append(f"**Product:** {pkg.get('product', 'CueLiez')}")
    lines.append(f"**Package type:** {pkg.get('epistemic_status', 'observed_indicator')} (observed indicators and cues only)")
    lines.append(f"**Definitive finding:** {pkg.get('is_definitive_finding', False)}")
    lines.append(f"**Origin:** {pkg.get('origin', 'grounded')}")
    if pkg.get("session_id"):
        lines.append(f"**Session ID:** {pkg.get('session_id')}")
    if pkg.get("seal_id"):
        lines.append(f"**Seal ID:** {pkg.get('seal_id')}")
    if pkg.get("sealed_at"):
        lines.append(f"**Sealed at (unix):** {pkg.get('sealed_at')}")
    if pkg.get("package_hash"):
        lines.append(f"**Package hash:** {pkg.get('package_hash')}")
    lines.append("")
    lines.append("## Notice")
    lines.append("")
    lines.append(EXPORT_NOTICE)
    if disclaimer:
        lines.append("")
        lines.append(f"**Disclaimer:** {disclaimer}")
    lines.append("")
    lines.append("## Gate / Consent Status (at a glance)")
    lines.append("")
    lines.append(f"- Mode/context: {gates.get('mode') or 'not specified in package annotations'}")
    lines.append(f"- Consent rechecked at seal: {gates.get('consent_rechecked')}")
    lines.append(f"- Training rechecked at seal: {gates.get('training_rechecked')}")
    dc = gates.get("dual_control_records")
    if dc is not None:
        lines.append(f"- Dual-control records present: {len(dc) if isinstance(dc, list) else 'yes'}")
    iu = gates.get("intended_uses")
    if iu is not None:
        lines.append(f"- Intended uses: {', '.join(map(str, iu)) if isinstance(iu, list) else iu}")
    lines.append("")
    lines.append("## Observation Cues")
    lines.append("")
    if not cue_events:
        lines.append("No observation cues were present at export thresholds.")
    else:
        lines.append("| Priority | Turn | Cue ID | Label | Score | Message |")
        lines.append("|---|---:|---|---|---:|---|")
        for c in cue_events:
            msg = str(c.get("message") or "").replace("|", "\\|").replace("\n", " ")
            turn = c.get("turn_index")
            lines.append(f"| {c.get('priority','')} | {turn if turn is not None else ''} | {c.get('cue_id','')} | {c.get('label','')} | {float(c.get('score') or 0):.2f} | {msg} |")
    lines.append("")
    lines.append("## Officer Notes on Cues")
    lines.append("")
    if not notes:
        lines.append("No officer notes/actions recorded.")
    else:
        for n in notes:
            lines.append(f"- **{n.get('cue_id')}** [{n.get('action','noted')}]"
                         + (f" (officer {n.get('officer_id')})" if n.get('officer_id') else "")
                         + f": {n.get('note') or '(no text)'}")
    lines.append("")
    lines.append("## Raw Observation Count")
    lines.append("")
    lines.append(f"- Observations in package: {len(obs)}")
    lines.append(f"- Cues rendered: {len(cue_events)}")
    lines.append(f"- Officer note records: {len(notes)}")
    lines.append("")
    lines.append("---")
    lines.append("Generated for review and evidence-system attachment without reinterpretation. Observed indicators and cues only.")
    return "\n".join(lines)


def render_package_summary_html(
    package: Mapping[str, Any],
    *,
    cues: Optional[Sequence[CueEvent | Mapping[str, Any]]] = None,
    observations: Optional[Sequence[Mapping[str, Any]]] = None,
    title: str = "CueLiez Sealed Package Summary",
) -> str:
    """Render a human-readable HTML summary (print/PDF-friendly)."""
    md = render_package_summary_markdown(package, cues=cues, observations=observations)
    # Simple, dependency-free HTML wrapper. Markdown table rows are kept readable in <pre> fallback
    # and key sections are rendered structurally.
    pkg = dict(package)
    obs = list(observations) if observations is not None else list(pkg.get("observations") or [])
    cue_events = [c.to_dict() if isinstance(c, CueEvent) else dict(c) for c in (cues or [c.to_dict() for c in cues_from_observations(obs)])]
    notes = normalize_officer_cue_notes(pkg.get(OFFICER_CUE_NOTES_KEY))
    gates = _gate_summary(pkg)
    disclaimer = html.escape(str(pkg.get("disclaimer") or ""))
    notice = html.escape(EXPORT_NOTICE)
    rows = []
    for c in cue_events:
        rows.append("<tr>"
                    f"<td>{html.escape(str(c.get('priority','')))}</td>"
                    f"<td>{html.escape(str(c.get('turn_index','')))}</td>"
                    f"<td><code>{html.escape(str(c.get('cue_id','')))}</code></td>"
                    f"<td>{html.escape(str(c.get('label','')))}</td>"
                    f"<td>{float(c.get('score') or 0):.2f}</td>"
                    f"<td>{html.escape(str(c.get('message','')))}</td>"
                    "</tr>")
    cue_body = "\n".join(rows) or "<tr><td colspan='6'>No observation cues were present at export thresholds.</td></tr>"
    note_items = "".join(f"<li><strong>{html.escape(str(n.get('cue_id')))}</strong> [{html.escape(str(n.get('action','noted')))}]: {html.escape(str(n.get('note') or '(no text)'))}</li>" for n in notes) or "<li>No officer notes/actions recorded.</li>"
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
    code {{ font-size: 12px; }}
    .meta dt {{ font-weight: 600; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p><strong>Product:</strong> {html.escape(str(pkg.get('product','CueLiez')))} &nbsp;|&nbsp;
     <strong>Status:</strong> {html.escape(str(pkg.get('epistemic_status','observed_indicator')))} (observed indicators and cues only) &nbsp;|&nbsp;
     <strong>Definitive finding:</strong> {html.escape(str(pkg.get('is_definitive_finding', False)))}</p>
  <div class="notice"><p><strong>Notice:</strong> {notice}</p><p><strong>Disclaimer:</strong> {disclaimer}</p></div>
  <h2>Gate / Consent Status</h2>
  <ul>
    <li>Mode/context: {html.escape(str(gates.get('mode') or 'not specified in package annotations'))}</li>
    <li>Consent rechecked at seal: {html.escape(str(gates.get('consent_rechecked')))}</li>
    <li>Training rechecked at seal: {html.escape(str(gates.get('training_rechecked')))}</li>
  </ul>
  <h2>Observation Cues</h2>
  <table><thead><tr><th>Priority</th><th>Turn</th><th>Cue ID</th><th>Label</th><th>Score</th><th>Message</th></tr></thead><tbody>{cue_body}</tbody></table>
  <h2>Officer Notes on Cues</h2>
  <ul>{note_items}</ul>
  <h2>Counts</h2>
  <ul><li>Observations in package: {len(obs)}</li><li>Cues rendered: {len(cue_events)}</li><li>Officer note records: {len(notes)}</li></ul>
  <hr/>
  <p>Generated for review and evidence-system attachment without reinterpretation. Observed indicators and cues only.</p>
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
) -> Dict[str, str]:
    """Export a sealed package to requested formats. Returns paths by format."""
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    if "json" in formats:
        paths["json"] = export_package_json(package, root / f"{basename}.json")
    if "md" in formats or "markdown" in formats:
        p = root / f"{basename}.summary.md"
        p.write_text(render_package_summary_markdown(package, cues=cues, observations=observations) + "\n", encoding="utf-8")
        paths["md"] = str(p)
    if "html" in formats:
        p = root / f"{basename}.summary.html"
        p.write_text(render_package_summary_html(package, cues=cues, observations=observations) + "\n", encoding="utf-8")
        paths["html"] = str(p)
    return paths
