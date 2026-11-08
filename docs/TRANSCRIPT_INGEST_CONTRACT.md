# Transcript Ingest Contract (stable path)

**Status:** Phase 7 integration readiness (no live Axon/RMS integration required).  
**Rule:** Observation and cues only — never findings. Sealed packages are the attachable artifacts.

## Supported JSON shapes

`load_transcript` / `build_ingested_package` accept:
- A **turn sequence**: `[{ "role": "...", "text": "...", ... }, ...]`
- A **wrapper object** with `turns`, `transcript`, or `messages` containing a turn sequence
- A **file path** (JSON), JSON string, or file-like object

Turns may include optional metadata used by observers (timestamps, pre-extracted feature summaries such as `prosody`/`audio_features`/`features` where lawful and consent-governed). No raw audio/video is required by the text-first path.

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
  "turn_count": <n or null>
}
```

`source_artifact` is **non-finding metadata** (original artifact reference). It is preserved by the seal path and included in canonical package content/hash.

## Seal and custody

To produce an attachable sealed artifact: build the package, attach any officer notes **before** seal, then seal via `cueliez.gates.seal_observation_package` / `cueliez.session.seal` with appropriate `SessionGateState` (fail-closed gates). Attach the **sealed JSON package** as the original artifact; see `docs/DEPLOYMENT_PRIVACY_CUSTODY.md` and `docs/ADMISSIBILITY_AND_DISCLOSURE.md`.
