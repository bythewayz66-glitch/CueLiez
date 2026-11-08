"""Operator-facing CLI entry point for CueLiez.

Accepts a transcript, runs observations/pack, applies gates when requested,
generates cues, seals a package, and exports results. The interface is explicit
about what the system does and does not do.

Dry demo (sample fixture):
  PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json --no-seal --show-cues
  PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json \\
    --mode interrogation --consent --attested-by officer-a \\
    --training-ack --training-version v1 --out-dir ./out
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .delivery import OnscreenCueRenderer, cues_from_observations
from .delivery.notes import attach_officer_cue_notes, normalize_officer_cue_notes
from .export import export_sealed_package
from .gates import SessionGateState, check_prohibited_uses, record_consent, seal_observation_package
from .observations import default_runner, full_runner
from .packs import get_pack

HONEST_NOTICE = (
    "CueLiez observes transcript/text signals and produces observation cues for human review. "
    "It does not determine credibility or produce findings. Gates and human judgment remain required."
)


def _load_transcript(path: Optional[str]) -> List[Dict[str, Any]]:
    if path and path != "-":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        data = json.load(sys.stdin)
    if isinstance(data, dict) and "transcript" in data:
        data = data["transcript"]
    if isinstance(data, list):
        return list(data)
    raise ValueError("Transcript input must be a JSON array of turns or an object with a 'transcript' array.")


def _load_json_file(path: Optional[str]) -> Optional[Any]:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cueliez",
        description="CueLiez operator entry point: transcript -> observations/cues -> gated sealed package + exports.",
        epilog="Sample fixture: docs/examples/sample_transcript.json (run with --no-seal for a dry demo).",
    )
    p.add_argument("transcript", nargs="?", default="-", help="Transcript JSON file, or '-' for stdin.")
    p.add_argument("--pack", help="Cue pack id (e.g., gov, leg, med, thrp). If omitted, uses runner.")
    p.add_argument("--runner", choices=["default", "full"], default="default", help="Observation runner when --pack is not set.")
    p.add_argument("--mode", choices=["generic", "interrogation", "therapy", "clinical", "government"], default="generic", help="Gate/session mode.")
    p.add_argument("--consent", action="store_true", help="Record affirmative consent (requires --attested-by for gated modes).")
    p.add_argument("--attested-by", help="Consent attester ID (officer/clinician identifier).")
    p.add_argument("--subject-id", help="Optional subject/session subject identifier.")
    p.add_argument("--jurisdiction", help="Optional jurisdiction/context label.")
    p.add_argument("--training-ack", action="store_true", help="Acknowledge operator training.")
    p.add_argument("--training-version", help="Training version identifier (required with --training-ack in gated modes).")
    p.add_argument("--intended-use", action="append", default=[], dest="intended_uses", help="Intended use label. May be repeated.")
    p.add_argument("--high-priority-cue-id", action="append", default=[], dest="high_priority_cue_ids", help="Cue ID requiring dual-control in government mode before seal.")
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
        check_prohibited_uses(args.intended_uses)

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
            if args.mode == "generic":
                state.mode = pack.mode  # align gates to pack unless explicitly generic requested? keep explicit mode precedence
                args.mode = pack.mode
            raw_package = pack.build_package(transcript, annotations=annotations)
            observations = raw_package.get("observations") or []
        else:
            state = SessionGateState(mode=args.mode, intended_uses=list(args.intended_uses), jurisdiction=args.jurisdiction, subject_id=args.subject_id)
            runner = full_runner() if args.runner == "full" else default_runner()
            raw_package = runner.build_package(transcript, annotations=annotations)
            observations = raw_package.get("observations") or []

        if args.consent and args.attested_by:
            record_consent(state, attested_by=args.attested_by, subject_id=args.subject_id, jurisdiction=args.jurisdiction)
        if args.training_ack:
            state.training_acknowledged = True
            if args.training_version:
                state.training_version = args.training_version

        cues = cues_from_observations(observations, min_score=args.min_score, max_cues=args.max_cues)
        if args.show_cues:
            print(OnscreenCueRenderer().render_text(cues, header="CueLiez Observation Cues"))
            print()

        package = dict(raw_package)
        officer_notes = _load_json_file(args.officer_notes)
        if officer_notes is not None:
            if isinstance(officer_notes, dict) and "officer_cue_notes" in officer_notes:
                officer_notes = officer_notes["officer_cue_notes"]
            package = attach_officer_cue_notes(package, officer_notes)

        if not args.no_seal:
            package = seal_observation_package(package, state, high_priority_cue_ids=args.high_priority_cue_ids)

        formats = args.formats or ["json", "md", "html"]
        exported = {}
        if args.out_dir:
            exported = export_sealed_package(package, args.out_dir, basename=args.basename, formats=formats, cues=cues, observations=observations)
            print(json.dumps({"ok": True, "notice": HONEST_NOTICE, "cue_count": len(cues), "observation_count": len(observations), "sealed": not args.no_seal, "exports": exported}, ensure_ascii=False))

        if args.print_json or not args.out_dir:
            print(json.dumps(package, indent=2, ensure_ascii=False))

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
