# TODO.md — Agent-Readable Task List for CueLiez

**Goal:** Turn CueLiez into a production-ready, compliance-first interview-assist layer that supports both **credibility** and **admissibility**, with a realistic path toward becoming a standard integration target (Axon, CaseCracker, RMS, etc.) in the $50–150M+ ARR range long-term.

All work must obey `AGENTS.md` and `docs/LANGUAGE_RULES.md`.

Status key: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Phase 0 — Stabilize the Skeleton (Immediate, 2–4 weeks)

- [x] Add minimal real dependencies to `pyproject.toml` (pydantic for schemas, numpy/scipy or equivalent for basic signal features, keep pytest). (Decision: no new runtime deps added; rule-based observers use stdlib only. pytest remains optional test dep. Conformance: only add deps actually used.)
- [x] Ensure default and full observation runners produce usable output on sample transcripts. (Phase 0 closeout: kilo smoke tests; default/full runners contract-valid on sample + owner transcripts.)
- [x] Make GitHub Pages live; ensure landing page and docs emphasize “Not a lie detector”. (Phase 0 closeout: glyph Pages workflow/review staging + site/docs language audit + test_site_language.)
- [x] Create a simple CLI or notebook that accepts transcript JSON → emits sealed package + cue list. (`python -m cueliez` operator entry point; applies gates when configured and exports cues/package.)
- [x] Confirm language tests and gate tests pass on current main.
- [x] Version the canonical disclaimer and reference it from seal path and docs. (Phase 0 closeout: iceman `DISCLAIMER_VERSION` embedded in sealed package and referenced in schema/admissibility docs.)

---

## Phase 1 — Production-Grade Observers (1–3 months)

- [x] Keep existing heuristic/rule observers as the fast, explainable baseline. (Phase 1+2: kilo kept rule-based baseline; assisted prototype optional, off by default.)
- [x] Layer lightweight ML / LLM-assisted observers for high-value signals (hedging, pronoun distancing, detail vagueness, claim conflicts, timeline inconsistency) behind feature flags or model_id versioning. (Phase 1+2: kilo design doc + optional prototype `assisted.py` with `ASSISTED_OBSERVERS_ENABLED=False`; not enabled in runners/packs. No external ML in production path.)
- [x] Ensure every observer emits gate-compatible observations (score + model_id + neutral label). (Phase 1+2: kilo contract tests.)
- [x] Add confidence calibration and explicit “insufficient data” / no-cue states. (Phase 1+2: kilo documented heuristic [0,1] calibration; insufficient-data/no-cue tests.)
- [x] Document model versions and provenance for every observer that is not pure rule-based. (Phase 1+2: kilo design doc + OBSERVER_INVENTORY updates.)
- [x] Expand test coverage for new observers (neutral labels, confidence bounds, no verdict language). (Phase 1+2: kilo tests.)

---

## Phase 2 — Gated Modalities & Real-Time Delivery (2–4 months)

- [x] Keep feature / physiological / visual observers gated; do not enable by default in packs. (Phase 1+2: kilo docs/gated design; assisted observers off by default.)
- [x] Build explicit consent + jurisdiction checks before enabling audio feature extraction or any camera/wearable input. (Implemented in `gates.py`: `record_modality_consent`/`require_gated_modality` with GateError codes; tests.)
- [x] Prioritize audio-only real-time path first (prosody, speech rate, latency, pause patterns). (Gated prosody observers implemented; consent-governed; documented.)
- [x] Implement officer-facing delivery (onscreen overlay / tablet cues) that the subject does not see by default. (Low-distraction officer HTML surface + structured officer-only panel with turn-linked/glanceable cues, confidence/method provenance display, and acknowledge/dismiss/note capture; `LiveDashboardServer` stdlib real-time dashboard; subject not shown this stream by default.)
- [x] Add optional officer response / note field for high-priority cues; include it in the sealed package. (Glyph capture/normalize/attach/export implemented; iceman confirmed seal preservation and canonical hash coverage; E2E verified.)
- [x] Target end-to-end latency < 1–2 seconds for text cues on local or private-cloud instance. (Local 2026-11-08 reference: owner fixtures default text path ~2–5 ms in-process observe+cues+render; ~275–390 ms end-to-end CLI subprocess, `--no-seal`; environment-specific, not a guarantee. Documented in `docs/demo/VALIDATION_NOTES.md`.)

---

## Phase 3 — Admissibility Hardening (Parallel, start immediately)

### 3.1 Language & Epistemic Status
- [x] Audit all code, docs, UI strings, and package fields for forbidden terms. (Phase 3: kilo observer surface + glyph site/docs/exports audits + language tests extended.)
- [x] Force `epistemic_status = "observed_indicator"` and `is_definitive_finding = false` at every seal.
- [x] Embed canonical disclaimer in every sealed package.
- [x] Reject banned annotation keys and verdict labels at seal time (already partially present — complete and test). (Phase 3: iceman banned keys/verdict labels rejected with GateError codes + tests.)

### 3.2 Consent, Training, Dual-Control Capture
- [x] Ensure full gate state (consent attester + timestamp, training version, dual-control records, intended uses) is serialized into the sealed package.
- [x] Make consent / training / dual-control failures produce clear, auditable GateError codes. (Phase 3: iceman stable codes.)
- [x] Add tests that prove packages cannot be sealed without required gates in high-stakes modes. (Phase 3: iceman tests.)

### 3.3 Package Integrity & Export
- [x] Define and implement a stable sealed-package schema (JSON) that includes observations, cues, gate state, disclaimer, product/version, seal timestamp, session identifiers. (Iceman seal path + glyph export surfaces; `schema_version`/`gate_state`/`product_version`/`package_hash` present when sealed.)
- [x] Add cryptographic hash (and later signature) of the package at seal time. (SHA-256 `package_hash` implemented by iceman; signature not yet implemented.)
- [x] Provide durable export formats: signed/structured JSON + human-readable PDF. (Structured JSON + human-readable Markdown/HTML summaries; HTML is print/PDF-friendly. Cryptographic signing not yet implemented.)
- [x] Prevent post-seal mutation of observations or epistemic fields. (Phase 3: iceman re-seal refusal + broader immutability; glyph pre-seal note attach refusal.)

### 3.4 Human Judgment Preservation
- [x] Officer action/note field for high-priority cues is optional but sealed when present. (Glyph capture/attach/export; iceman seal/hash confirmed; attach refused after seal.)
- [x] Package never records automated legal, clinical, or credibility findings. (Enforced by seal epistemic forcing, language rules, and tests.)
- [x] Clear separation in schema and docs between “system observed/suggested” and “human decided”. (Export/onscreen framing separates system-observed cues from officer notes/human review.)

### 3.5 Documentation for Disclosure
- [x] Write first version of **Admissibility & Disclosure Guide** (what is/isn’t in the package, how consent/training/dual-control appear, recommended disclosure handling). (`docs/ADMISSIBILITY_AND_DISCLOSURE.md` v1 exists; glyph aligned export/disclosure wording and print-to-PDF guidance as observation-only.)
- [x] Keep sales, training, and UI language consistent with technical reality. (Glyph audited delivery/export/site/demo/docs/deployment shipped surfaces; `test_site_language` scans key docs; sales/training outlines remain <= never-claim and no-accuracy.)
- [x] Prepare short internal validation notes (false-positive / over-cue rates, officer utility) that do **not** claim truth-detection accuracy. (`docs/demo/VALIDATION_NOTES.md`.)

---

## Phase 4 — Privacy, Security, Integration

- [x] Design primarily for on-prem / air-gapped / private-cloud deployment (CJIS / equivalent readiness). (Glyph `docs/deployment/READINESS.md`; operator guidance. Not certification.)
- [x] Document data-retention and access controls for sealed packages. (Glyph documented operator responsibilities, artifact handling, least-privilege/access/retention guidance in `docs/deployment/READINESS.md` and demo docs; technical enforcement pending.)
- [x] Integration priority order:
  1. Transcript ingest from existing systems (Axon, CaseCracker, etc.)
  2. Real-time audio stream hooks
  3. Officer UI (tablet overlay or simple web dashboard)
  4. Export into RMS / case / evidence management systems
  (Documented in TODO/owner posture; first-pilot uses transcript ingest/export only, no live integrations.)
- [x] Make sealed packages easy to attach as original artifacts rather than derivative interpretations. (Glyph documented canonical `sealed_package.json`+`package_hash` as original artifact, summaries as observation-only aids, RMS/case attachment workflow; no live RMS connector.)

---

## Phase 5 — Validation & Evidence of Value

- [x] Build private red-team / synthetic + de-identified transcript set for regression and utility testing. (Owner synthetic demos + red-team fixtures; broader private set pending partner data.)
- [ ] Partner with 1–2 academic or practitioner groups in investigative interviewing for small controlled studies (officer follow-up quality, review usefulness, over-cue rates).
- [x] Target early pilot agencies that already record interviews and care about PEACE / cognitive interviewing standards. (Glyph updated `docs/demo/PILOT_PREP.md` targeting/framing; partnerships/outreach pending.)
- [x] Measure and report latency, completeness of packages, and gate compliance in pilots. (Glyph documented manual local timing/completeness/gate observation paths; no truth-detection accuracy claims.)

---

## Phase 6 — Go-to-Market & Commercial

- [~] Pricing experiments that match positioning (per-seat / per-session SaaS or on-prem + support; higher tiers for government dual-control and multi-modality). (Glyph documented no-accuracy positioning/pricing guardrails in pilot-prep docs; experiments pending.)
- [~] Productize existing training gates into an operator certification / training program. (Glyph added docs-only training/certification outline; program productization pending.)
- [ ] Explore partnerships with interview-room hardware and evidence-platform vendors.
- [x] Never market accuracy-of-deception, confession rates, or automated decisions. (Locked in owner decisions/language rules; glyph docs/tests reinforce.)
- [x] Primary message: clearer inquiry + auditable record of observations and cues, fairer and tighter for both the guilty and the innocent. (Aligned in docs/messaging.)

---

## Phase 7 — Integration & Gated Modalities Enablement (post-pilot, partner-driven)

Added per owner direction after faster-than-expected completion of Phases 0–5. Do not start by default; enable only on explicit partner demand and consent/policy support.

- [x] Live Axon / CaseCracker / RMS integration (transcript ingest → sealed package attachment) when a pilot partner supplies transcript export. (Phase 7: iceman ingest validation + kilo normalizer + glyph CLI push/pull with mocked endpoints; env-based config, no hardcoded creds.)
- [ ] Real-time audio stream hooks (prosody, speech rate, latency, pause patterns) behind explicit consent + jurisdiction checks. Not started: the observers exist, nothing feeds them from a live source. Superseded and scheduled by Phase 10 (Phase A0/A1), per owner decision 2026-11-11; prosody/voice-quality features are excluded from the live path in `docs/design/LIVE_AV_PRODUCT_SCOPE.md`.
- [x] Officer UI (tablet overlay or simple web dashboard) for real-time cues, subject not shown by default. (Glyph: officer HTML subject-hidden with ack/dismiss/note; real CLI `--stream-turns` live cue updates; `LiveDashboardServer` stdlib HTTP dashboard with polling + subject-not-shown notice. Full websocket/live-audio dashboard optional.)
- [x] Export into RMS / case / evidence management systems as original artifacts (not derivative interpretations). (Glyph docs: canonical `sealed_package.json`+`package_hash` attachable as original artifact; summaries observation-only aids; no live RMS connector.)
- [ ] Enable physiological / visual / wearable observers only with consent-governed policy support and clinical/therapy messaging kept out of pilot scope. Split by owner decision 2026-11-11: visual (video-derived) is scheduled as Phase 10 Phase B with an entry gate; physiological and wearable stay out.
- [ ] Government mode external pilot only if a specific partner demands it (dual-control enforced).
- [ ] Clinical / therapy packs remain present in code but out of pilot messaging unless explicitly scoped.

---

## Phase 8 — Enable All Gated Modalities by Default (post-pilot, policy-approved)

Added per owner direction. Turns currently gated/off-by-default modalities and features to **on by default** only after policy/consent frameworks are approved. Do not enable without consent + jurisdiction checks and training acknowledgement.

- [ ] Enable feature/physiological/visual observers by default in packs (currently gated/off).
- [ ] Enable audio feature extraction (prosody, speech rate, latency, pause patterns) by default where consent + jurisdiction checks pass. Not started; same note as camera: the 2026-11-11 decision does not make this default.
- [ ] Enable camera/wearable input by default where consent + jurisdiction checks pass. Not started and not implied by the 2026-11-11 live AV decision, which makes live inputs available per session after consent, never default. Needs its own owner decision.
- [ ] Enable real-time streaming officer UI by default (currently batch/CLI-first).
- [ ] Enable government mode external pilot by default (dual-control enforced).
- [ ] Enable clinical/therapy packs in pilot messaging where explicitly scoped.
- [ ] Update consent/training gates to reflect new defaults; re-verify admissibility checklist.

---

## Admissibility Requirements Checklist (Quick Reference)

Copy of the living checklist — expand into formal acceptance criteria as items are implemented.

**Language & Epistemic**
- [x] No forbidden terms anywhere in shipped surface. (Language tests + audits.)
- [x] Forced observed_indicator / non-definitive status at seal.
- [x] Canonical disclaimer present. (Versioned.)

**Gates**
- [x] Consent + attester before required modes.
- [x] Training version recorded.
- [x] Dual-control for government high-priority cues.
- [x] Prohibited uses blocked.

**Observation Quality**
- [x] score + model_id + neutral label on every observation.
- [x] Reproducible under same model versions.

**Package Integrity**
- [x] Hash/signature at seal. (Hash implemented; signature optional hook.)
- [x] Full gate state + cues + observations exported.
- [x] No post-seal mutation.

**Human Judgment**
- [x] Officer notes sealed when present.
- [x] No automated findings.

**Export & Custody**
- [x] Durable JSON + PDF (or equivalent). (JSON + MD/HTML; HTML print/PDF-friendly.)
- [x] Works with evidence / RMS workflows. (Docs; no live connector.)

**Docs**
- [x] Admissibility & Disclosure Guide exists and is accurate.

---

## Immediate Next Actions for Agents

1. Read `AGENTS.md` and `docs/LANGUAGE_RULES.md` fully.
2. Complete Phase 0 items that are still open.
3. Implement or tighten seal-time capture of full gate state into the package.
4. Draft the first Admissibility & Disclosure Guide (can live under `docs/`).
5. Add package hashing at seal time.
6. Keep all new observers and UI strings behind the language and epistemic rules.

---

**Source of this list:** Consolidated from product evaluation, market context, next-steps plan, game plan to remove current limitations, and the Admissibility Requirements discussion (2026-11-07).

---

## Phase 9 — Path to A+ (Deep Scan Remediation, appended 2026-11-09)

**Source:** Deep scan report card (Glyph Cluster session, 2026-11-09). All work must obey `AGENTS.md` and `docs/LANGUAGE_RULES.md`. No fake code, no placeholders, no stubs. Observation/cue-only framing; no verdict, diagnosis, or deception-determination features.

Status key: `[ ]` not started · `[~]` in progress · `[x]` done

### 9.1 Fake coding / stubs / placeholder impls (current A- → A+)
- [x] Add/maintain a CI/static check that fails on `TODO|FIXME|XXX|NotImplementedError|raise NotImplemented|pass  # stub|implement later` in `src/` (allow explicit, reviewed exceptions only with documented rationale). (Sprint 2 - 2026-11-09: `scripts/check_no_fake_code.py` + `tests/test_hygiene_phase9.py`; wired in `.github/workflows/ci.yml`. Reviewed-exception allowlist mechanism remains minimal and should be expanded only with documented rationale.)
- [ ] Keep `assisted.py` prototype behavior explicitly fail-closed and non-fabricating; add a contract test asserting disabled/unwired assisted observers never emit verdict-shaped data or external calls without explicit opt-in/config.
- [ ] Audit any future `return None/[]/{}` paths: require comments/tests distinguishing legitimate “no data / insufficient data / disabled” guards from incomplete behavior.
- [ ] Remove or clearly label non-runtime “placeholder” UI/help strings only where they could be misread as implementation gaps (current hits like `{id}` endpoint templates and HTML input placeholders are acceptable if documented).

### 9.2 Drift (current B+ → A+)
- [x] Remove local/committed drift artifacts: ensure `build/`, `dist/`, `*.egg-info` build outputs, and `__pycache__`/`*.pyc` are never tracked; add CI check (`git ls-files`/clean-tree guards) for ignored build/bytecode artifacts. (Sprint 2 - 2026-11-09: `scripts/check_no_tracked_artifacts.py` + CI; local untracked artifact cleanup done.)
- [x] Add release/version consistency checks: `pyproject.toml` version, `src/cueliez/__init__.__version__`, changelog/tag (if adopted), and schema/package metadata must match; fail CI on skew. (Sprint 2 - 2026-11-09: `scripts/check_version_consistency.py` + CI; changelog/tag/schema metadata checks can be expanded.)
- [~] Add a “docs vs implementation” verification pass in CI for critical surfaces (CLI flags/help snapshots or tests, gate error codes, schema fields, export formats, disclaimer/version references). (Sprint 2 + follow-ups 2026-11-09: CI includes help smoke, `scripts/check_cli_contract.py` (required flags), and `scripts/check_contracts_phase9.py` (sealed schema/epistemic/hash, export formats, disclaimer/observed-indicator framing, key gate-code presence). Follow-up: full gate-error code registry snapshots, schema version migrations, and richer docs snapshot tests.)
- [ ] Keep `TODO.md` status claims evidence-backed; for any `[x]` item that is docs/operator-only (not technically enforced), append “(docs/operator guidance; technical enforcement pending)” or split into separate enforced/documented items.

### 9.3 Documentation (current A- → A+)
- [ ] Add/verify operator-facing docs for every shipped CLI flag, export format, connector env var, and gate error code; generate or test-help snapshots to prevent drift.
- [ ] Add a production operations runbook: deployment modes (on-prem/air-gapped/private cloud), secure config, backup/restore of sealed artifacts, incident handling, and explicit non-certification/non-legal-opinion boundaries.
- [ ] Document cryptographic integrity model precisely: what `package_hash` covers, canonicalization rules, signature hook status, and verification procedure; add examples.
- [ ] Add API/module reference docs (or docstring coverage checks) for `gates`, `session`, `ingest`, `connectors`, `export`, `delivery`, and `observations` contracts.
- [ ] Add a “known limitations / not production-certified” doc section aligned with current reality (SSRF hardening pending, no bundled signer, no live vendor connectors, retention enforcement operator-controlled, training/cert framework only).

### 9.4 Training & certification program (current C → A+)
- [x] Define scope explicitly (Sprint 4 - 2026-11-09): added `docs/compliance/TRAINING_CERT_SCOPE.md` and referenced it from `docs/compliance/README.md`; clarifies training/gate integration vs full certification/LMS and observation-only scope boundaries.
- [~] Build a **training records system** (Sprint 4 + follow-up 2026-11-09): added minimal persistent technical record support `src/cueliez/compliance/records.py` (`TrainingCredentialRecord`, `TrainingRecordStore` JSONL append-only events, record hashes, issue/verify/revoke/get, expiry/status, gate-compatible ack) with minimal RBAC controls (`enforce_rbac`, `admin_actors`, actor checks; `CUELIEZ_TRAINING_ENFORCE_RBAC`/`CUELIEZ_TRAINING_ADMIN_ACTORS`) and admin audit events. Tests: `tests/test_training_records_phase9.py`. Not a full LMS/access-controlled enterprise system; follow-up: secure storage/encryption, jurisdiction/org linkage, richer governance/workflows, and external identity integration.
- [~] Implement **credential/certificate issuance** (Sprint 4 + follow-up 2026-11-09, minimal): unique credential IDs, verify/status/expiry/revocation in `TrainingRecordStore`, actor/RBAC checks and admin audit hooks; observation-safe scope documented. Follow-up: formal certificate artifacts/export, suspended workflow, verification API/service, and governance.
- [ ] Implement **renewal/expiry/recertification**: policy-driven validity windows, version-change triggers, reminders/workflows (or interfaces), and gate behavior when training is expired (fail closed for required modes).
- [ ] Implement **assessment delivery/governance**: structured assessments (not caller-declared only), scoring/rubric, trainer/proctor authorization, approval workflow, and auditable admin actions.
- [ ] Add **governance/RBAC and audit trails** for training administration: roles, separation of duties where appropriate, immutable event log for issuance/revocation/updates, and identity/HR integration interfaces (with privacy controls).
- [ ] Add **privacy/records handling** for training data consistent with deployment policy; document retention/access and provide technical controls where feasible.
- [ ] Add end-to-end tests: valid/invalid ack, expired/renewed training, revoked credential, version mismatch, and gate enforcement in all training-required modes.

### 9.5 Functionality & domain completeness (current B+ → A+)
- [ ] Complete a domain-by-domain acceptance matrix (gates, consent, memory/seal, observations, session, ingest, connectors, delivery, export, packs, CLI) with explicit “production-ready / gated / framework / operator-dependent” status and tests.
- [ ] Harden `memory`/seal lifecycle docs+tests for contamination controls, partition behavior, and post-seal immutability across all APIs/exports.
- [ ] Formalize observation contracts: required fields (`score`, `model_id`, neutral label, evidence/provenance as applicable), insufficient-data behavior, and calibration documentation per observer.
- [ ] Make assisted/ML/LLM observer integration fully policy-gated with provenance, model/version pinning, offline/local options where required, and explicit opt-in; never default-enable in high-stakes modes without approvals.
- [ ] Validate real-time/audio-stream semantics end-to-end (derived features only, consent/jurisdiction/modality gates, latency/error behavior, cue deduplication) with documented limits.
- [ ] Ensure every domain pack (gov/leg/med/thrp) has reviewed observer sets, guidance, gate defaults, and tests; keep out-of-scope packs clearly marked in product messaging.

### 9.6 Feature coverage (current B → A+)
- [x] Implement cryptographic **signing and verification** workflow (Sprint 5 + follow-ups 2026-11-09, HMAC-SHA256, stdlib): added `src/cueliez/signing.py` (`load_signing_key`/`load_verification_keys`, `hmac_sign_package`, `verify_hmac_signature` with `key`/`keys` rotation support via `CUELIEZ_SIGNING_VERIFY_KEYS`, `hmac_signer`) over canonical `package_hash`; `package_signature` remains excluded from hash (stable). Key custody documented in `docs/deployment/KEY_CUSTODY.md`. CLI: `--sign` (requires configured key) and `--verify-package <file>` (hash + optional signature verification); `session.seal` passes `signer`. Tests: `tests/test_signing_phase9.py`, `tests/test_cli_verify_sign_phase9.py`. Follow-up: asymmetric/KMS options if needed, formal key-rotation/overlap policy docs per deployment, and default signing policy decisions.
- [ ] Add durable, reproducible export verification tooling (hash/signature check, schema validation, completeness report) as CLI/library commands.
- [ ] Improve real-time officer UI options: authenticated local dashboard mode, configurable polling/WebSocket (if added), accessibility basics, and explicit subject-not-shown controls; preserve observation-only framing.
- [ ] Add structured officer workflow features only where human-led: cue acknowledgement/notes disposition metadata, review queues, and export of human actions separately labeled from system observations.
- [ ] Expand modality support only behind explicit consent+jursdiction+policy gates with clear data minimization (derived features preferred; raw sensor handling only if explicitly designed and approved).

### 9.7 Integration coverage (current B- → A+)
- [ ] Evolve connectors from generic HTTP to **hardened integration adapters**: per-integration config schemas, endpoint/credential validation, idempotency keys, retries/backoff policies, payload size limits, and audit events.
- [ ] Add vendor-specific integration adapters only when partner contracts/scope exist (Axon, CaseCracker, RMS, case/evidence systems), with mocked conformance tests and live-integration test plans run only in approved environments.
- [ ] Define and test RMS/case/evidence attachment workflows as first-class flows: canonical sealed package + hash/signature + disclosure summary + chain-of-custody metadata mapping (observation-only).
- [ ] Add streaming ingest integration contracts (real-time transcript/audio-derived feature hooks) with backpressure, ordering/timestamp rules, replay protection, and fail-closed behavior on gate failures.
- [ ] Provide stable machine-readable integration contracts (OpenAPI/JSON Schema where appropriate) for push/pull/export payloads and version them.

### 9.8 Production readiness / gaps (current C+ → A+)
- [x] **SSRF/egress hardening (priority, Sprint 1 - 2026-11-09):** `src/cueliez/connectors.py` validates connector URLs (http/https only, no embedded credentials), resolves hostnames, allows loopback for local/on-host tooling, blocks link-local/metadata always, blocks multicast/unspecified/reserved, blocks RFC1918/CGNAT/private ranges by default with explicit opt-in `CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK=1` for approved on-prem targets; supports `CUELIEZ_CONNECTOR_HOST_ALLOWLIST` (hostnames/CIDRs); revalidates redirects with hop limit; enforces request/response size caps. Tests: `tests/test_connectors_security_phase9.py`; existing connector tests still pass. Follow-up: service-context threat-model review and optional stricter default `https` policy mode.
- [x] **Path/output hardening (Sprint 1 - 2026-11-09, export layer):** `src/cueliez/export.py` sanitizes export basenames, prevents path traversal/escape from output dir, resolves outputs safely, and sets restrictive file permissions (`0600`) where supported. Tests: `tests/test_export_security_phase9.py`; existing export/e2e tests still pass. Follow-up: apply same hardening to any remaining CLI/service file-input paths and configurable permission policy.
- [~] **Structured observability (Sprint 3 + follow-ups 2026-11-09):** added `src/cueliez/audit.py` (stdlib JSON-line audit events, redaction/truncation, best-effort, optional `CUELIEZ_AUDIT_LOG`/`CUELIEZ_AUDIT_STDERR`, thread-local correlation context); integrated redacted events for connector URL/egress validation, requests/responses (host/status/bytes, no tokens/full content), export operations, and `gate.seal` summary events. CLI sets per-run correlation ID; connector `push_package`/`pull_package`/request path accept optional `correlation_id`. Follow-up: propagate correlation/session IDs through all service contexts, centralized audit sink/levels, and retention/access controls per policy.
- [ ] **Technical data controls (where feasible):** configurable retention hooks/policies, encryption-at-rest guidance/integration points, access control integration for stored packages, and secure deletion workflows; keep operator/legal policy boundaries explicit.
- [~] **Dashboard/service hardening (Sprint 3 + follow-up 2026-11-09):** `LiveDashboardServer` defaults to localhost; optional token auth; rejects non-allowed `Origin` headers (localhost allowed by default, `CUELIEZ_DASHBOARD_ALLOWED_ORIGINS` configurable; missing Origin allowed for programmatic clients) with 403; in-memory per-IP rate limiting (429). Tests: `tests/test_dashboard.py`. Follow-up: TLS/reverse-proxy guidance, authenticated browser UI flow, distributed rate limiting, and stronger CSRF/session controls for exposed deployments.
- [ ] **Supply chain & CI/CD:** add CI (pytest, language/site checks, packaging, schema/contract tests, security/static checks), dependency review (even with minimal runtime deps), SBOM/release process, and signed release artifacts if distributed.
- [ ] **Deployment packaging:** provide reproducible deployment artifacts (container/non-container as appropriate), config schema/examples, health/readiness checks for service modes, and backup/restore procedures.
- [ ] **Security review:** threat model (STRIDE-style or equivalent), penetration checklist for connectors/dashboard/CLI service wrappers, and remediation tracking; avoid any feature that enables prohibited surveillance or automated findings.

### 9.9 Mega-polish / hygiene (current B → A+)
- [~] Clean working tree hygiene in dev/release process: remove local `build/` and `__pycache__`; enforce via CI/pre-commit. (2026-11-09: removed untracked local `build/`/`__pycache__` artifacts in working tree; CI/pre-commit enforcement pending.)
- [ ] Add repo quality gates: formatting/lint/type checks as adopted by project style, pre-commit hooks, and consistent import/module organization; keep changes minimal and aligned with existing style.
- [ ] Add/confirm license header policy (if desired) and third-party notice handling; keep Apache-2.0 compliance clear.
- [ ] Add coverage for edge cases discovered by scans: connector URL abuse cases, malformed transcripts, gate-state serialization/immutability, export hash/signature verification, and dashboard endpoint misuse.
- [ ] Run periodic “mega polish” audits (fake-code scan, drift scan, language-rule audit, security checklist, docs-contract checks) and record findings in `DIARY.md`/issue tracker with evidence.

---

## Phase 10 — Live Audio and Video Cues (owner decision 2026-11-11)

**Owner decision, 2026-11-11** (relayed by the lead dev): "CueLiez will give cues during a LIVE interview from live AUDIO and live VIDEO inputs, not only text transcripts." Supersedes the `docs/OWNER_DECISIONS.md` section 2 row that kept visual input out of the first pilot, for audio and video only. Never-claim paragraph and all gates unchanged. Scope, hard rules, wording and acceptance criteria: `docs/design/LIVE_AV_PRODUCT_SCOPE.md`. Engineering design: `docs/design/LIVE_AV_DESIGN.md`. All items below are not started as of 2026-11-11; mark done only after the lead dev verifies the acceptance criteria in the scope document.

- [ ] Phase A0: live microphone to local speech-to-text to finalised turns into the stream path; per-modality consent (`audio_capture`); officer live-inputs strip and kill switch; modality record and state timeline in the sealed package.
- [ ] Phase A1: derived audio-timing cues (latency, speech rate, pauses), separately consented and switchable, baseline-relative wording with fixed caveats.
- [ ] Phase B entry gate: counsel answers, cited literature review, Phase A over-cue report reviewed by the owner.
- [ ] Phase B: live video as derived features only (off-camera gaze, blink rate, movement); frames in memory only; lowest-priority cues; separate `camera` consent.
- [ ] Live-input cue wording gate at seal and in the observers (no inner-state words; `gaze aversion` renamed).
- [ ] Live AV training addendum and counsel-approved consent form text (PM drafts; counsel approves).
