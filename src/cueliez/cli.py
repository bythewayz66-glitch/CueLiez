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
from pathlib import Path
from typing import Any, Dict, List, Optional

from .delivery import OnscreenCueRenderer, cues_from_observations
from .delivery.notes import attach_officer_cue_notes
from .export import export_sealed_package
from .gates import GateError, SessionGateState, record_consent
from .session import assert_can_observe, seal
from .observations import default_runner, full_runner
from .packs import get_pack

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
    p.add_argument("--no-seal", action="store_true", help="Build observations/cues only; do not apply seal.")
    p.add_argument("--print-json", action="store_true", help="Print final package JSON to stdout.")
    return p


def run_cli(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        transcript = _load_transcript(args.transcript)

        annotations: Dict[str, Any] = {
            "mode": args.mode,
            "intended_uses": list(args.intended_uses),
            "operator_notice": HONEST_NOTICE,
        }
        if args.pack:
            pack = get_pack(args.pack)
            state = pack.make_gate_state(intended_uses=list(args.intended_uses), jurisdiction=args.jurisdiction, subject_id=args.subject_id)
            annotations["cue_pack"] = pack.id
            annotations["cue_pack_mode"] = pack.mode
            if args.mode != "generic":
                state.mode = args.mode
            else:
                args.mode = state.mode
                annotations["mode"] = state.mode
        else:
            pack = None
            state = SessionGateState(mode=args.mode, intended_uses=list(args.intended_uses), jurisdiction=args.jurisdiction, subject_id=args.subject_id)

        if args.consent:
            if not args.attested_by:
                raise GateError("consent_attester_required", "--consent requires --consent-attester/--attested-by.")
            record_consent(state, attested_by=args.attested_by, subject_id=args.subject_id, jurisdiction=args.jurisdiction)
        if args.training_ack or args.training_version:
            state.training_acknowledged = True
            if args.training_version:
                state.training_version = args.training_version

        # Session lifecycle (iceman API): fail closed before observation.
        assert_can_observe(state)

        if pack is not None:
            raw_package = pack.build_package(transcript, annotations=annotations)
            observations = raw_package.get("observations") or []
        else:
            runner = full_runner() if args.runner == "full" else default_runner()
            raw_package = runner.build_package(transcript, annotations=annotations)
            observations = raw_package.get("observations") or []

        cues = cues_from_observations(observations, min_score=args.min_score, max_cues=args.max_cues)
        hi_ids = _high_priority_cue_ids(cues)

        if args.show_cues:
            print(OnscreenCueRenderer().render_text(cues, header="CueLiez Observation Cues"))
            print()

        if args.print_high_priority_cue_ids:
            print(json.dumps({"high_priority_cue_ids": hi_ids, "notice": HONEST_NOTICE}, ensure_ascii=False))
            if not args.continue_after_print:
                return 0

        package = dict(raw_package)
        officer_notes = _load_json_file(args.officer_notes)
        if officer_notes is not None:
            if isinstance(officer_notes, dict) and "officer_cue_notes" in officer_notes:
                officer_notes = officer_notes["officer_cue_notes"]
            if _package_is_sealed(package):
                raise GateError("sealed_package_immutable", "Officer notes must be attached before seal; package is already sealed.")
            package = attach_officer_cue_notes(package, officer_notes)

        if not args.no_seal:
            dual_ids = list(args.high_priority_cue_ids) or (hi_ids if state.mode == "government" else [])
            package = seal(package, state, high_priority_cue_ids=dual_ids)

        formats = args.formats or ["json", "md", "html"]
        if args.out_dir:
            exported = export_sealed_package(package, args.out_dir, basename=args.basename, formats=formats, cues=cues, observations=observations)
            print(json.dumps({"ok": True, "notice": HONEST_NOTICE, "cue_count": len(cues), "observation_count": len(observations), "high_priority_cue_ids": hi_ids, "sealed": not args.no_seal, "exports": exported}, ensure_ascii=False))

        if args.print_json or not args.out_dir:
            print(json.dumps(package, indent=2, ensure_ascii=False, default=str))

        return 0
    except Exception as e:
        payload = {"ok": False, "error": str(e), "notice": HONEST_NOTICE}
        if hasattr(e, "code"):
            payload["error_code"] = getattr(e, "code")
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
