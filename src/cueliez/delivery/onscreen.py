"""Onscreen cue rendering for professionals.

Produces human-readable and structured display payloads. All rendered text must
remain non-verdict and cue-oriented.
"""

from __future__ import annotations

import html
import json
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .events import CueEvent, PRIORITY_ORDER, cues_from_observations

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
            lines.append(header)
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
            line = f"{prefix}{c.onscreen_text} (score={c.score:.2f}, {c.category})"
            lines.append(line)
            if self.show_evidence and c.evidence_summary:
                ev = json.dumps(c.evidence_summary, ensure_ascii=False)
                dim = _ANSI["dim"] if self.use_color else ""
                rst = _ANSI["reset"] if self.use_color else ""
                lines.append(f"           {dim}evidence: {ev}{rst}")
        lines.append("Notice: cues are probabilistic observations for professional judgment, not determinations.")
        return "\n".join(lines)

    def render_panel(self, observations: Sequence[Mapping[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        cues = cues_from_observations(observations, **{k: v for k, v in kwargs.items() if k in ("min_score", "max_cues")})
        counts: Dict[str, int] = {}
        for c in cues:
            counts[c.priority] = counts.get(c.priority, 0) + 1
        return {
            "type": "cueliez_onscreen_cues",
            "cue_count": len(cues),
            "priority_counts": counts,
            "cues": [c.to_dict() for c in cues],
            "text": self.render_text(cues, header=kwargs.get("header")),
            "notice": "Observation cues for professional review; not findings.",
        }

    def render_html(self, cues: Sequence[CueEvent], *, title: str = "CueLiez Observation Cues") -> str:
        rows = []
        for c in cues:
            ev = html.escape(json.dumps(c.evidence_summary, ensure_ascii=False)) if c.evidence_summary else ""
            rows.append(
                "<tr>"
                f"<td class='p {html.escape(c.priority)}'>{html.escape(c.priority.upper())}</td>"
                f"<td>{html.escape(str(c.turn_index) if c.turn_index is not None else '—')}</td>"
                f"<td>{html.escape(c.category)}</td>"
                f"<td>{html.escape(c.message)}</td>"
                f"<td>{c.score:.2f}</td>"
                f"<td><code>{ev}</code></td>"
                "</tr>"
            )
        body = "\n".join(rows) or "<tr><td colspan='6'>No observation cues at current thresholds.</td></tr>"
        return (
            "<section class='cueliez-cues'>"
            f"<h2>{html.escape(title)}</h2>"
            "<p class='notice'>Observation cues for professional review; not findings.</p>"
            "<table><thead><tr><th>Priority</th><th>Turn</th><th>Category</th><th>Cue</th><th>Score</th><th>Evidence</th></tr></thead>"
            f"<tbody>{body}</tbody></table></section>"
        )
