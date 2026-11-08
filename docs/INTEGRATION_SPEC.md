# Integration Spec — CueLiez (vendor-facing)

**Product:** CueLiez (Cue + Legal Interview Engine) — real-time signal observation and testimony cues for legal interviews. Not a lie detector.

**Status:** v1 integration posture. Transcript-export-first pilot; live connectors optional and partner-supplied.

---

## 1. Integration posture

- **No live Axon/RMS/CaseCracker integration required for v1.** Transcript-export-only pilot: partner supplies transcript export; CueLiez runs locally/private-cloud and returns a sealed package.
- **On-prem / private-cloud first.** No public SaaS required. Processing of interview content stays within the authorized environment boundary.
- **Sealed packages are original artifacts.** Attach canonical `sealed_package.json` (with `package_hash`) to RMS/case/evidence workflows; summaries are observation-only aids, not findings or substitutes.

## 2. Transcript ingest contract

Canonical input: an ordered list of turns. Each turn is an object with at least `role` and `text`. Accepted shapes:

- JSON array of turns: `[{"role":"officer","text":"..."}, {"role":"subject","text":"..."}]`
- Object with `transcript` or `turns` array: `{"transcript":[...]}` / `{"turns":[...]}`

Turn fields (canonical):
- `role` (string): `officer` or `subject` (aliases like `speaker` are accepted).
- `text` (string): utterance text.
- Optional metadata: `response_latency_ms`, timestamps, speaker IDs, etc. (passed through; not required).

Normalization is implemented in `cueliez.ingest` (`normalize_transcript`, `canonicalize_turn`, `validate_transcript_turns`). See `docs/TRANSCRIPT_INGEST_CONTRACT.md`.

## 3. Sealed package (output) schema

Canonical output: `sealed_package.json` with:
- `schema_version` (e.g., `"1.0"`), `product` (`"CueLiez"`), `product_version`
- `epistemic_status` = `"observed_indicator"`, `is_definitive_finding` = `false`, `origin` = `"grounded"`
- `disclaimer` + `disclaimer_version` (canonical, hash-based version)
- `sealed_at` (timestamp), `package_hash` (SHA-256 over canonical content excluding `sealed_at`/hash/signature)
- `gate_state` (mode, consent, attester, timestamp, training version, dual-control records, intended uses, requirements)
- `observations` (array): neutral `label`, `confidence.score` in [0,1], non-empty `confidence.model_id`, `method`, `category`, `evidence` (incl. `source_text`/`source_texts`, turn refs), `cue_id`, `priority`
- `annotations` (mode, intended uses, operator notice)
- `officer_cue_notes` (optional, human-authored, attached before seal)
- `package_signature` (optional, default null; excluded from hash)

See `docs/schemas/sealed_package_v1.md`.

## 4. Integrity verification

- Verify with `cueliez.gates.verify_package_hash(package)` (recompute SHA-256 over canonical content).
- `cueliez.gates.validate_sealed_package_ingest(package)` fail-closes on invalid hash, missing epistemic fields, or banned content.
- Hash is an integrity check of recorded observations/process — not proof of subject claims.

## 5. Connector contract (optional, partner-supplied)

Live connectors are optional and require partner-supplied endpoints/credentials:

- Env-based config (no hardcoded secrets):
  - `CUELIEZ_PUSH_ENDPOINT` / `--push-endpoint`
  - `CUELIEZ_PULL_ENDPOINT` / `--pull-endpoint`
  - `CUELIEZ_CONNECTOR_TOKEN` (Bearer) or `CUELIEZ_CONNECTOR_AUTH_HEADER`
  - `CUELIEZ_CONNECTOR_TIMEOUT`, retries via `--connector-retries`
- Push: POST final sealed package; optional evidence-bundle export after success.
- Pull: GET package by id (`{id}` placeholder or query), then export/render locally.
- Offline graceful: `ConnectorError` codes (`connector_unavailable`, `connector_http_error`, `connector_config_missing`, etc.).
- Tests use mocked local endpoints only (no live vendor access required).

CLI reference: `docs/demo/OPERATOR_DRY_RUN.md` (connector section).

## 6. Evidence/case attachment

- Attach canonical `sealed_package.json` as an original artifact; preserve `package_hash`, `schema_version`, `product_version`, disclaimer/epistemic fields, `gate_state`.
- Summaries (MD/HTML, print-to-PDF) are observation-only aids, not findings or substitutes.
- Officer notes are human-authored and attached before seal.
- No live RMS connector required for v1; operator-controlled/manual attachment supported.

## 7. Language and compliance guardrails

- Forbidden in all shipped text: lie detector, detects lies, truth score, polygraph, proves deception, guilty/not guilty (as system output), diagnosis (as system output), definitive deception claims.
- Required vocabulary: observation, signal, indicator, cue, inconsistency, officer assist, probabilistic, confidence-scored, sealed observed indicator.
- Never-claim paragraph (`docs/OWNER_DECISIONS.md` §1) must appear (or strict paraphrase) in any external description.

## 8. First-pilot scope

- Modes: `generic` + `interrogation` only.
- On-prem / private-cloud processing preferred.
- Gated modalities (audio features, camera, wearable) off by default; explicit consent + jurisdiction required.
- No live Axon/RMS integration required unless a partner supplies transcript export.

## Contact

Product owner (human). Repository: `bythewayz66-glitch/CueLiez`. All materials subject to `AGENTS.md` and `docs/LANGUAGE_RULES.md`.