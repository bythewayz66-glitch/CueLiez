# Transcript Ingest Contract (stable path)

**Status:** Phase 7 integration readiness (no live Axon/RMS integration required).  
**Rule:** Observation and cues only — never findings. Sealed packages are the attachable artifacts.

## Supported JSON shapes

`load_transcript` / `build_ingested_package` accept a **file path** (JSON), a JSON string, a file-like object, or an already-parsed value, whose content is either:
- A **turn sequence** at the root: `[{ "role": "...", "text": "...", ... }, ...]`
- A **wrapper object** with exactly one recognised turn container whose value is a list of turns.

**WRAPPER_KEYS:** `turns`, `transcript`, `messages`, `utterances`, `segments`, `items`, `entries`, `results`, `dialogue`, `conversation`

Other keys on a wrapper object (meeting ids, vendor metadata) are not turns. They are not silently dropped: their names are listed in `ingest_report.ignored_wrapper_keys`.

Turns may include optional metadata used by observers (timestamps, pre-extracted feature summaries such as `prosody`/`audio_features`/`features` where lawful and consent-governed). No raw audio/video is required by the text-first path.

## Turn normalisation

`cueliez.ingest` maps common field aliases to canonical turns. The aliases are common-shape mappings covered by mocked fixtures in `tests/fixtures/transcripts/vendor/`; they are not claims about any vendor's proprietary API.

**ROLE_KEYS:** `role`, `speaker`, `speaker_role`, `speakerRole`, `speaker_type`, `speakerType`, `participant`, `participant_role`, `participantRole`, `channel`, `label`, `actor`

**TEXT_KEYS:** `text`, `utterance`, `content`, `transcript`, `body`, `message`, `value`

**TOKEN_KEYS:** `words`, `tokens`

Rules, all enforced and tested:
- A turn that is a **string** becomes `{role: "subject", text: <string>}`. This is an assumed attribution.
- A turn that is not an object or a string (number, null, list, bool) is rejected with `ingest_invalid_turn`. Null turns are never skipped.
- **Role.** The first `ROLE_KEYS` field that maps to `subject` or `interviewer` is used. The mapping is the alias table in `ingest.py` (for example `suspect`, `witness` map to `subject`; `officer`, `Detective B` map to `interviewer`). If the turn has no role field, or none maps, it is rejected with `ingest_unattributed_turn`, naming the turn index and the original label. If two role fields map to different roles, the turn is rejected with `ingest_ambiguous_turn`. When the original label differs from the canonical role it is kept as `speaker_original`.
- **Text.** The first non-blank `TEXT_KEYS` field is used; if none, `TOKEN_KEYS` are joined with spaces. If two text fields hold different non-blank text, the turn is rejected with `ingest_ambiguous_turn`. A text field that is not a string or a list of words/objects is rejected with `ingest_invalid_turn`.
- **Nothing else is dropped.** Every other key on the turn (timestamps, ids, feature containers, nested objects, the unused alias fields, `words`/`tokens`) is copied to the canonical turn unchanged. A blank-but-present `role`/`text` field that would collide with the canonical keys is kept under `ingest_unmapped`.
- Turn order and count are preserved: the accepted turn count equals the input turn count or the whole input is rejected.

## Empty turns

A turn whose role is mapped but whose text is empty or whitespace is an **empty turn**.

**EMPTY_TEXT_POLICY:** `flag`

`ingest.EMPTY_TEXT_POLICY` is the single policy switch; every ingest function also takes `empty_text_policy=` to override it per call. Both policies are implemented and tested:
- `flag` (default, the product manager's decision recorded in `DIARY.md` 2026-11-11): the turn is kept at its original position with `ingest_flags: ["empty_text"]`, and listed in `ingest_report.flagged_turns` as `{"index": i, "code": "empty_text"}`. Any timing or feature metadata on it (silence or pause segments) is kept.
- `reject`: the turn is rejected with `ingest_empty_turn` naming the turn index, **unless** it carries non-text content (any timing or feature key below), in which case it is kept and flagged exactly as under `flag`.

**NON_TEXT_CONTENT_KEYS:** `start`, `end`, `start_time`, `end_time`, `startTime`, `endTime`, `start_ms`, `end_ms`, `timestamp`, `time`, `offset`, `offset_ms`, `duration`, `duration_ms`, `duration_s`, `speech_duration_ms`, `speech_duration_s`, `response_latency_ms`, `latency_ms`, `delay_ms`, `response_latency_s`, `latency_s`, `pause_total_ms`, `pause_duration_ms`, `silence_ms`, `pause_count`, `prosody`, `acoustic`, `audio_features`, `features`, `gaze_aversion_ratio`, `blink_rate`, `heart_rate_bpm`, `hrv_ms`, `hrv_rmssd_ms`

Under both policies, a transcript with zero turns, or in which every turn is empty, is rejected with `ingest_empty_transcript`. There is no threshold on the share of empty turns.

## Genuinely empty input

Empty input is never an empty transcript. `[]`, `{"turns": []}`, `None`, and a transcript whose turns are all empty raise `ingest_empty_transcript` (or `ingest_unrecognised_structure` for `None`, which is not a transcript at all).

## Errors

Every failure raises `cueliez.ingest.IngestError`, a `ValueError` subclass with `.code`, `.message`, `.turn_index` (or `None`) and `.as_dict()`; `str(e)` is `[code] message`. The CLI's top-level handler prints `error_code` for any exception with a `code` and exits non-zero. Codes are also listed in `docs/GATE_ERROR_CODES.md`.

**INGEST_ERROR_CODES:** `ingest_invalid_input`, `ingest_invalid_turn`, `ingest_ambiguous_turn`, `ingest_unattributed_turn`, `ingest_empty_turn`, `ingest_unrecognised_structure`, `ingest_ambiguous_structure`, `ingest_empty_transcript`

| Code | Raised when |
|------|-------------|
| `ingest_invalid_input` | the file cannot be read or is not valid JSON |
| `ingest_invalid_turn` | a turn is not an object or string, or a text field has an unusable type |
| `ingest_ambiguous_turn` | a turn has conflicting role fields or conflicting text fields |
| `ingest_unattributed_turn` | a turn has no role field, or none maps to `subject`/`interviewer` |
| `ingest_empty_turn` | `reject` policy only: empty text and no timing/feature content |
| `ingest_unrecognised_structure` | the root is not a list or wrapper object, a wrapper has no recognised container, or the container is not a list |
| `ingest_ambiguous_structure` | a wrapper object has more than one recognised container |
| `ingest_empty_transcript` | zero turns, or every turn is empty |

An invalid `empty_text_policy` value raises a plain `ValueError` (programmer error, not input error).

## Ingest report

`normalize_transcript_with_report(source)` returns `(turns, report)`. `build_ingested_package` puts the report in `source_artifact.ingest_report`, which is part of the package hash and preserved by the seal path.

**INGEST_REPORT_FIELDS:** `input_turn_count`, `accepted_turn_count`, `container`, `ignored_wrapper_keys`, `flagged_turns`, `empty_text_policy`

`container` is the wrapper key used, or `root` for a bare list. With `include_source_artifact=False` no report is attached.

APIs: `normalize_transcript(source)`, `normalize_transcript_with_report(source)`, `canonicalize_turn(turn)`, `validate_transcript_turns(turns)`. Normalized transcripts are runner-compatible.

## Stable API (`cueliez.ingest`)

- `load_transcript(source) -> normalized transcript`
- `transcript_source_hash(transcript) -> sha256 hex` (canonical JSON integrity reference)
- `build_ingested_package(source, *, runner=None, session_id=None, annotations=None, include_source_artifact=True) -> observation package`

`build_ingested_package` runs observers (default runner unless provided) and may attach neutral `source_artifact` metadata:

```json
{
  "type": "transcript_json",
  "name": "<path or null>",
  "transcript_sha256": "<sha256>",
  "turn_count": <n>,
  "ingest_report": { ... see Ingest report ... }
}
```

`source_artifact` is **non-finding metadata** (original artifact reference). It is preserved by the seal path and included in canonical package content/hash.

## Seal and custody

To produce an attachable sealed artifact: build the package, attach any officer notes **before** seal, then seal via `cueliez.gates.seal_observation_package` / `cueliez.session.seal` with appropriate `SessionGateState` (fail-closed gates). Attach the **sealed JSON package** as the original artifact; see `docs/DEPLOYMENT_PRIVACY_CUSTODY.md` and `docs/ADMISSIBILITY_AND_DISCLOSURE.md`.

## Connector ingest validation (sealed packages)

Connectors that attach/receive sealed packages should validate before accepting as original artifacts:

- `cueliez.gates.validate_sealed_package_ingest(package)` (also exported from `cueliez`) — fail-closed; verifies sealed state, completeness, `package_hash`, and non-finding epistemic fields. Returns a minimal receipt on success.
- Auditable `GateError` codes: `ingest_invalid_package`, `ingest_not_sealed`, `ingest_hash_mismatch`, `ingest_epistemic_invalid`, `connector_validation_failed`.
- Connector transport/config failures should use `connector_auth_failed`, `connector_config_missing`, `connector_network_error` (see `docs/GATE_ERROR_CODES.md`). No hardcoded credentials; use environment configuration. Tests must mock external access.
