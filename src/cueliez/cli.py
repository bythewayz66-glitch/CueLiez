"""Operator-facing CLI entry point for CueLiez.

Accepts a transcript, runs observations/pack, applies gates when requested,
generates cues, seals a package, and exports results. The interface is explicit
about what the system does and does not do.

Dry demo (sample fixture):
  PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json --no-seal --show-cues
  PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json \\
    --mode interrogation --consent --consent-attester officer-a \\
    --training-version v1 --out-dir ./out
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .delivery import OnscreenCueRenderer, cues_from_observations
from .delivery.notes import attach_officer_cue_notes
from .export import export_sealed_package
from .connectors import ConnectorError, push_endpoint, pull_endpoint, push_package, pull_package
from .audit import set_audit_correlation_id
from .gates import GateError, SessionGateState, record_consent, verify_package_hash
from .session import assert_can_observe, seal
from .observations import default_runner, full_runner
from .observations.assisted import make_multi_signal_assisted_adapter, register_assisted_observer, merge_assisted_observations, clear_assisted_registry
from .packs import get_pack
from .signing import hmac_signer, load_signing_key, verify_hmac_signature

HONEST_NOTICE = (
    "CueLiez observes transcript/text signals and produces observation cues for human review. "
    "It does not determine credibility or produce findings. Gates and human judgment remain required."
)


def _normalize_transcript_turn(turn: Any) -> Any:
    if not isinstance(turn, dict):
        return turn
    if "role" not in turn and "speaker" in turn:
        out = dict(turn)
        out["role"] = out.get("speaker")
        return out
    return turn


def _load_transcript(path: Optional[str]) -> List[Dict[str, Any]]:
    if path and path != "-":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        data = json.load(sys.stdin)
    if isinstance(data, dict):
        if "transcript" in data:
            data = data["transcript"]
        elif "turns" in data:
            data = data["turns"]
    if isinstance(data, list):
        return [_normalize_transcript_turn(t) for t in data]
    raise ValueError(
        "Transcript input must be a JSON array of turns, or an object with a 'transcript' or 'turns' array."
    )


def _load_json_file(path: Optional[str]) -> Optional[Any]:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _package_is_sealed(package: Dict[str, Any]) -> bool:
    return bool(package.get("sealed_at") or package.get("package_hash") or package.get("sealed") is True)


def _high_priority_cue_ids(cues) -> List[str]:
    return [c.cue_id for c in cues if getattr(c, "priority", "") in {"high", "critical"}]


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cueliez",
        description="CueLiez operator entry point: transcript -> observations/cues -> gated sealed package + exports.",
        epilog=(
            "Sample fixtures: docs/examples/sample_transcript.json, docs/examples/conflict_transcript.json. "
            "For non-generic modes, provide required consent/training flags before observation."
        ),
    )
    p.add_argument("transcript", nargs="?", default="-", help="Transcript JSON file, or '-' for stdin.")
    p.add_argument("--pack", help="Cue pack id (e.g., gov, leg, med, thrp). If omitted, uses runner.")
    p.add_argument("--runner", choices=["default", "full"], default="default", help="Observation runner when --pack is not set.")
    p.add_argument("--mode", choices=["generic", "interrogation", "therapy", "clinical", "government"], default="generic", help="Gate/session mode.")
    p.add_argument("--consent", action="store_true", help="Record affirmative consent (with --consent-attester/--attested-by).")
    p.add_argument("--consent-attester", "--attested-by", dest="attested_by", help="Consent attester ID (officer/clinician identifier).")
    p.add_argument("--subject-id", help="Optional subject/session identifier.")
    p.add_argument("--jurisdiction", help="Optional jurisdiction/context label.")
    p.add_argument("--training-ack", action="store_true", help="Acknowledge operator training.")
    p.add_argument("--training-version", help="Training version identifier (required by gated modes when training is acknowledged/required).")
    p.add_argument("--intended-use", action="append", default=[], dest="intended_uses", help="Intended use label. May be repeated.")
    p.add_argument("--high-priority-cue-id", action="append", default=[], dest="high_priority_cue_ids", help="Cue ID requiring dual-control in government mode before seal.")
    p.add_argument("--list-high-priority", "--print-high-priority-cue-ids", dest="print_high_priority_cue_ids", action="store_true", help="List high-priority cue IDs for dual-control workflow.")
    p.add_argument("--continue-after-print", action="store_true", help="With --list-high-priority, continue to seal/export after printing.")
    p.add_argument("--officer-notes", help="JSON file containing officer cue notes/actions to attach before sealing.")
    p.add_argument("--out-dir", help="Directory to write exported package files.")
    p.add_argument("--basename", default="sealed_package", help="Export basename.")
    p.add_argument("--format", action="append", choices=["json", "md", "html"], dest="formats", help="Export format. May be repeated. Default: json,md,html.")
    p.add_argument("--min-score", type=float, default=0.0, help="Minimum cue score to include in cue output.")
    p.add_argument("--max-cues", type=int, help="Maximum cues to render/export.")
    p.add_argument("--show-cues", action="store_true", help="Print rendered cue text to stdout.")
    p.add_argument("--enable-assisted", action="store_true", help="Enable feature-flagged assisted (multi-signal) observers. Off by default; no external ML. Requires approved deployment.")
    p.add_argument("--no-seal", action="store_true", help="Build observations/cues only; do not apply seal.")
    p.add_argument("--print-json", action="store_true", help="Print final package JSON to stdout.")
    p.add_argument("--sign", action="store_true", help="Sign the sealed package using HMAC-SHA256 when CUELIEZ_SIGNING_KEY/CUELIEZ_SIGNING_KEY_FILE is configured.")
    p.add_argument("--verify-package", help="Verify a sealed package JSON file (hash + optional HMAC signature when key configured) and exit.")
    p.add_argument("--stream-turns", action="store_true", help="Real-time mode: read NDJSON turns (one JSON object per line) from transcript/stdin, emit newly surfaced observation cues as turns arrive (subject not shown). Final package/seal runs after stream ends unless --no-seal.")
    p.add_argument("--push-endpoint", help="HTTP endpoint to POST the final sealed package to after a successful run (overrides CUELIEZ_PUSH_ENDPOINT). Env-based auth: CUELIEZ_CONNECTOR_TOKEN / CUELIEZ_CONNECTOR_AUTH_HEADER. No hardcoded credentials.")
    p.add_argument("--pull-endpoint", help="HTTP endpoint to GET a sealed package from (supports {id} placeholder or ?id=; overrides CUELIEZ_PULL_ENDPOINT).")
    p.add_argument("--pull-id", help="Sealed package ID to pull via --pull-endpoint/CUELIEZ_PULL_ENDPOINT, then export/render locally (skips transcript observation).")
    p.add_argument("--connector-timeout", type=float, default=15.0, help="Connector HTTP timeout in seconds.")
    p.add_argument("--connector-retries", type=int, default=2, help="Connector retry count for transient/offline errors.")
    p.add_argument("--training-gui", action="store_true", help="Launch the web-based Training GUI (modules, media, interactive quizzes, sandbox, records). Not a CLI training workflow.")
    p.add_argument("--training-gui-host", default="127.0.0.1", help="Training GUI host.")
    p.add_argument("--training-gui-port", type=int, default=911, help="Training GUI port.")
    return p
