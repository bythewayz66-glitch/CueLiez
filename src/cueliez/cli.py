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
from .connectors import ConnectorError, push_endpoint, pull_endpoint, push_package, pull_package
from .gates import GateError, SessionGateState, record_consent
from .session import assert_can_observe, seal
from .observations import default_runner, full_runner
from .observations.assisted import make_multi_signal_assisted_adapter, register_assisted_observer, merge_assisted_observations, clear_assisted_registry
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
    p.add_argument("--enable-assisted", action="store_true", help="Enable feature-flagged assisted (multi-signal) observers. Off by default; no external ML. Requires approved deployment.")
    p.add_argument("--no-seal", action="store_true", help="Build observations/cues only; do not apply seal.")
    p.add_argument("--print-json", action="store_true", help="Print final package JSON to stdout.")
    p.add_argument("--stream-turns", action="store_true", help="Real-time mode: read NDJSON turns (one JSON object per line) from transcript/stdin, emit newly surfaced observation cues as turns arrive (subject not shown). Final package/seal runs after stream ends unless --no-seal.")
    p.add_argument("--push-endpoint", help="HTTP endpoint to POST the final sealed package to after a successful run (overrides CUELIEZ_PUSH_ENDPOINT). Env-based auth: CUELIEZ_CONNECTOR_TOKEN / CUELIEZ_CONNECTOR_AUTH_HEADER. No hardcoded credentials.")
    p.add_argument("--pull-endpoint", help="HTTP endpoint to GET a sealed package from (supports {id} placeholder or ?id=; overrides CUELIEZ_PULL_ENDPOINT).")
    p.add_argument("--pull-id", help="Sealed package ID to pull via --pull-endpoint/CUELIEZ_PULL_ENDPOINT, then export/render locally (skips transcript observation).")
    p.add_argument("--connector-timeout", type=float, default=15.0, help="Connector HTTP timeout in seconds.")
    p.add_argument("--connector-retries", type=int, default=2, help="Connector retry count for transient/offline errors.")
    return p


def _iter_ndjson_turns(path: Optional[str]):
    fh = open(path, "r", encoding="utf-8") if path and path != "-" else sys.stdin
    try:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield _normalize_transcript_turn(obj)
            elif isinstance(obj, list):
                for t in obj:
                    yield _normalize_transcript_turn(t)
    finally:
        if fh is not sys.stdin:
            fh.close()


def _run_stream_turns(args, state, pack, annotations):
    transcript: List[Dict[str, Any]] = []
    seen_cue_ids = set()
    renderer = OnscreenCueRenderer()
    print(json.dumps({"event": "stream_start", "notice": HONEST_NOTICE, "streaming": True, "subject_visible": False}, ensure_ascii=False), flush=True)
    runner = None if pack is not None else (full_runner() if args.runner == "full" else default_runner())
    for turn in _iter_ndjson_turns(args.transcript):
        transcript.append(turn)
        if pack is not None:
            raw_package = pack.build_package(transcript, annotations=annotations)
            observations = raw_package.get("observations") or []
        else:
            observations = runner.run(transcript)
            raw_package = {"observations": observations, "annotations": annotations}
        cues = cues_from_observations(observations, min_score=args.min_score, max_cues=args.max_cues, transcript=transcript)
        new_cues = [c for c in cues if c.cue_id not in seen_cue_ids]
        for c in new_cues:
            seen_cue_ids.add(c.cue_id)
        if new_cues:
            print(json.dumps({"event": "new_cues", "turn_count": len(transcript), "cues": [c.to_dict() for c in new_cues], "notice": HONEST_NOTICE}, ensure_ascii=False), flush=True)
        else:
            print(json.dumps({"event": "turn", "turn_count": len(transcript), "new_cue_count": 0}, ensure_ascii=False), flush=True)

    # Final result over full accumulated transcript
    if pack is not None:
        raw_package = pack.build_package(transcript, annotations=annotations)
        observations = raw_package.get("observations") or []
    else:
        runner = full_runner() if args.runner == "full" else default_runner()
        raw_package = runner.build_package(transcript, annotations=annotations)
        observations = raw_package.get("observations") or []
    cues = cues_from_observations(observations, min_score=args.min_score, max_cues=args.max_cues, transcript=transcript)
    hi_ids = _high_priority_cue_ids(cues)
    if args.show_cues:
        print(renderer.render_text(cues, header="CueLiez Observation Cues (final)"), flush=True)
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
    pend = push_endpoint(args.push_endpoint)
    push_result = None
    if pend:
        push_result = push_package(pend, package, timeout=args.connector_timeout, retries=args.connector_retries)
    exported = None
    if args.out_dir:
        exported = export_sealed_package(package, args.out_dir, basename=args.basename, formats=formats, cues=cues, observations=observations, transcript=transcript)
    if exported or push_result or args.out_dir:
        ev = {"ok": True, "event": "stream_end", "notice": HONEST_NOTICE, "cue_count": len(cues), "observation_count": len(observations), "high_priority_cue_ids": hi_ids, "sealed": not args.no_seal}
        if push_result:
            ev["push"] = {"status": push_result.get("status"), "endpoint": push_result.get("endpoint")}
        if exported:
            ev["exports"] = exported
        print(json.dumps(ev, ensure_ascii=False), flush=True)
    if args.print_json or (not args.out_dir and not push_result):
        print(json.dumps(package, indent=2, ensure_ascii=False, default=str), flush=True)
    elif not exported and not push_result and args.out_dir:
        print(json.dumps({"event": "stream_end", "ok": True, "cue_count": len(cues), "notice": HONEST_NOTICE}, ensure_ascii=False), flush=True)
    return 0


def run_cli(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        # Connector pull path: fetch an existing sealed package, then export/render (no observation).
        if args.pull_id:
            pend = pull_endpoint(args.pull_endpoint)
            if not pend:
                raise ConnectorError("connector_config_missing", "Pull requires --pull-endpoint or CUELIEZ_PULL_ENDPOINT.")
            pulled = pull_package(pend, args.pull_id, timeout=args.connector_timeout, retries=args.connector_retries)
            package = pulled.get("package") if isinstance(pulled.get("package"), dict) else pulled.get("response")
            if not isinstance(package, dict):
                raise ConnectorError("connector_invalid_response", "Pulled response did not contain a sealed package object.")
            observations = package.get("observations") if isinstance(package.get("observations"), list) else []
            cues = cues_from_observations(observations, min_score=args.min_score, max_cues=args.max_cues)
            if args.show_cues:
                print(OnscreenCueRenderer().render_text(cues, header="CueLiez Observation Cues (pulled)"))
                print()
            formats = args.formats or ["json", "md", "html"]
            result = {"ok": True, "action": "pull", "notice": HONEST_NOTICE, "package_id": args.pull_id, "endpoint": pulled.get("endpoint")}
            if args.out_dir:
                result["exports"] = export_sealed_package(package, args.out_dir, basename=args.basename, formats=formats, cues=cues, observations=observations)
            print(json.dumps(result, ensure_ascii=False))
            if args.print_json or not args.out_dir:
                print(json.dumps(package, indent=2, ensure_ascii=False, default=str))
            return 0

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

        if args.stream_turns:
            return _run_stream_turns(args, state, pack, annotations)

        transcript = _load_transcript(args.transcript)

        if pack is not None:
            raw_package = pack.build_package(transcript, annotations=annotations)
            observations = raw_package.get("observations") or []
        else:
            runner = full_runner() if args.runner == "full" else default_runner()
            raw_package = runner.build_package(transcript, annotations=annotations)
            observations = raw_package.get("observations") or []

        if getattr(args, "enable_assisted", False):
            clear_assisted_registry()
            register_assisted_observer("multi_signal", make_multi_signal_assisted_adapter())
            observations = merge_assisted_observations(observations, transcript, enabled=True)
            if isinstance(raw_package, dict):
                raw_package["observations"] = observations

        cues = cues_from_observations(observations, min_score=args.min_score, max_cues=args.max_cues, transcript=transcript)
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
        pend = push_endpoint(args.push_endpoint)
        push_result = None
        if pend:
            push_result = push_package(pend, package, timeout=args.connector_timeout, retries=args.connector_retries)
        exported = None
        # Evidence/package export can be triggered after a successful push when --out-dir is set.
        if args.out_dir:
            exported = export_sealed_package(package, args.out_dir, basename=args.basename, formats=formats, cues=cues, observations=observations, transcript=transcript)
        result = {"ok": True, "notice": HONEST_NOTICE, "cue_count": len(cues), "observation_count": len(observations), "high_priority_cue_ids": hi_ids, "sealed": not args.no_seal}
        if push_result:
            result["push"] = {"status": push_result.get("status"), "endpoint": push_result.get("endpoint")}
        if exported:
            result["exports"] = exported
        if args.out_dir or push_result:
            print(json.dumps(result, ensure_ascii=False))
        if args.print_json or (not args.out_dir and not push_result):
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
