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
- [ ] Real-time audio stream hooks (prosody, speech rate, latency, pause patterns) behind explicit consent + jurisdiction checks.
- [x] Officer UI (tablet overlay or simple web dashboard) for real-time cues, subject not shown by default. (Glyph: officer HTML subject-hidden with ack/dismiss/note; real CLI `--stream-turns` live cue updates; `LiveDashboardServer` stdlib HTTP dashboard with polling + subject-not-shown notice. Full websocket/live-audio dashboard optional.)
- [x] Export into RMS / case / evidence management systems as original artifacts (not derivative interpretations). (Glyph docs: canonical `sealed_package.json`+`package_hash` attachable as original artifact; summaries observation-only aids; no live RMS connector.)
- [ ] Enable physiological / visual / wearable observers only with consent-governed policy support and clinical/therapy messaging kept out of pilot scope.
- [ ] Government mode external pilot only if a specific partner demands it (dual-control enforced).
- [ ] Clinical / therapy packs remain present in code but out of pilot messaging unless explicitly scoped.

---

## Phase 8 — Enable All Gated Modalities by Default (post-pilot, policy-approved)

Added per owner direction. Turns currently gated/off-by-default modalities and features to **on by default** only after policy/consent frameworks are approved. Do not enable without consent + jurisdiction checks and training acknowledgement.

- [ ] Enable feature/physiological/visual observers by default in packs (currently gated/off).
- [ ] Enable audio feature extraction (prosody, speech rate, latency, pause patterns) by default where consent + jurisdiction checks pass.
- [ ] Enable camera/wearable input by default where consent + jurisdiction checks pass.
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
