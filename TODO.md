# TODO.md — Agent-Readable Task List for CueLiez

**Goal:** Turn CueLiez into a production-ready, compliance-first interview-assist layer that supports both **credibility** and **admissibility**, with a realistic path toward becoming a standard integration target (Axon, CaseCracker, RMS, etc.) in the $50–150M+ ARR range long-term.

All work must obey `AGENTS.md` and `docs/LANGUAGE_RULES.md`.

Status key: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Phase 0 — Stabilize the Skeleton (Immediate, 2–4 weeks)

- [ ] Add minimal real dependencies to `pyproject.toml` (pydantic for schemas, numpy/scipy or equivalent for basic signal features, keep pytest).
- [x] Ensure default and full observation runners produce usable output on sample transcripts. (Phase 0 closeout: kilo smoke tests; default/full runners contract-valid on sample + owner transcripts.)
- [x] Make GitHub Pages live; ensure landing page and docs emphasize “Not a lie detector”. (Phase 0 closeout: glyph Pages workflow/review staging + site/docs language audit + test_site_language.)
- [x] Create a simple CLI or notebook that accepts transcript JSON → emits sealed package + cue list. (`python -m cueliez` operator entry point; applies gates when configured and exports cues/package.)
- [x] Confirm language tests and gate tests pass on current main.
- [x] Version the canonical disclaimer and reference it from seal path and docs. (Phase 0 closeout: iceman `DISCLAIMER_VERSION` embedded in sealed package and referenced in schema/admissibility docs.)

---

## Phase 1 — Production-Grade Observers (1–3 months)

- [x] Keep existing heuristic/rule observers as the fast, explainable baseline. (Phase 1+2: kilo kept rule-based baseline; assisted prototype optional, off by default.)
- [~] Layer lightweight ML / LLM-assisted observers for high-value signals (hedging, pronoun distancing, detail vagueness, claim conflicts, timeline inconsistency) behind feature flags or model_id versioning. (Phase 1+2: kilo added design doc + optional prototype `assisted.py` with `ASSISTED_OBSERVERS_ENABLED=False`; not enabled in runners/packs.)
- [x] Ensure every observer emits gate-compatible observations (score + model_id + neutral label). (Phase 1+2: kilo contract tests.)
- [x] Add confidence calibration and explicit “insufficient data” / no-cue states. (Phase 1+2: kilo documented heuristic [0,1] calibration; insufficient-data/no-cue tests.)
- [x] Document model versions and provenance for every observer that is not pure rule-based. (Phase 1+2: kilo design doc + OBSERVER_INVENTORY updates.)
- [x] Expand test coverage for new observers (neutral labels, confidence bounds, no verdict language). (Phase 1+2: kilo tests.)

---

## Phase 2 — Gated Modalities & Real-Time Delivery (2–4 months)

- [x] Keep feature / physiological / visual observers gated; do not enable by default in packs. (Phase 1+2: kilo docs/gated design; assisted observers off by default.)
- [~] Build explicit consent + jurisdiction checks before enabling audio feature extraction or any camera/wearable input. (Phase 1+2: kilo documented consent/jurisdiction checks; implementation pending partner demand.)
- [~] Prioritize audio-only real-time path first (prosody, speech rate, latency, pause patterns). (Phase 1+2: kilo design doc for audio path; implementation pending.)
- [x] Implement officer-facing delivery (onscreen overlay / tablet cues) that the subject does not see by default. (Low-distraction officer HTML surface + structured officer-only panel with turn-linked/glanceable cues, confidence/method provenance display, and acknowledge/dismiss/note capture; subject not shown this stream by default. Not a real-time streaming overlay yet.)
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
- [~] Keep sales, training, and UI language consistent with technical reality. (Glyph audited delivery/export/site/demo/docs wording; broader sales/training surfaces remain to verify.)
- [ ] Prepare short internal validation notes (false-positive / over-cue rates, officer utility) that do **not** claim truth-detection accuracy.

---

## Phase 4 — Privacy, Security, Integration

- [~] Design primarily for on-prem / air-gapped / private-cloud deployment (CJIS / equivalent readiness). (Glyph documented on-prem/private-cloud posture in demo/disclosure docs; CJIS/equivalent operational readiness not implemented.)
- [~] Document data-retention and access controls for sealed packages. (Glyph added operator-responsibility guidance in demo/disclosure docs; technical controls not implemented.)
- [x] Integration priority order:
  1. Transcript ingest from existing systems (Axon, CaseCracker, etc.)
  2. Real-time audio stream hooks
  3. Officer UI (tablet overlay or simple web dashboard)
  4. Export into RMS / case / evidence management systems
  (Documented in TODO/owner posture; first-pilot uses transcript ingest/export only, no live integrations.)
- [~] Make sealed packages easy to attach as original artifacts rather than derivative interpretations. (Glyph documented canonical JSON+hash as primary artifact and summaries as observation-only aids; RMS workflow integration pending.)

---

## Phase 5 — Validation & Evidence of Value

- [~] Build private red-team / synthetic + de-identified transcript set for regression and utility testing. (Owner synthetic demos exist; broader private/de-identified set pending.)
- [ ] Partner with 1–2 academic or practitioner groups in investigative interviewing for small controlled studies (officer follow-up quality, review usefulness, over-cue rates).
- [~] Target early pilot agencies that already record interviews and care about PEACE / cognitive interviewing standards. (Glyph added pilot-prep framing/outline in `docs/demo/PILOT_PREP.md`; partnerships/targeting pending.)
- [~] Measure and report latency, completeness of packages, and gate compliance in pilots. (Glyph documented manual local timing/completeness/gate observation paths in demo/validation docs; no truth-detection accuracy claims.)

---

## Phase 6 — Go-to-Market & Commercial

- [~] Pricing experiments that match positioning (per-seat / per-session SaaS or on-prem + support; higher tiers for government dual-control and multi-modality). (Glyph documented no-accuracy positioning/pricing guardrails in pilot-prep docs; experiments pending.)
- [~] Productize existing training gates into an operator certification / training program. (Glyph added docs-only training/certification outline; program productization pending.)
- [ ] Explore partnerships with interview-room hardware and evidence-platform vendors.
- [x] Never market accuracy-of-deception, confession rates, or automated decisions. (Locked in owner decisions/language rules; glyph docs/tests reinforce.)
- [~] Primary message: clearer inquiry + auditable record of observations and cues, fairer and tighter for both the guilty and the innocent. (Aligned in docs/messaging with observation-only framing; external sales materials must remain ≤ never-claim.)

---

## Phase 7 — Integration & Gated Modalities Enablement (post-pilot, partner-driven)

Added per owner direction after faster-than-expected completion of Phases 0–5. Do not start by default; enable only on explicit partner demand and consent/policy support.

- [ ] Live Axon / CaseCracker / RMS integration (transcript ingest → sealed package attachment) when a pilot partner supplies transcript export.
- [ ] Real-time audio stream hooks (prosody, speech rate, latency, pause patterns) behind explicit consent + jurisdiction checks.
- [ ] Officer UI (tablet overlay or simple web dashboard) for real-time cues, subject not shown by default.
- [ ] Export into RMS / case / evidence management systems as original artifacts (not derivative interpretations).
- [ ] Enable physiological / visual / wearable observers only with consent-governed policy support and clinical/therapy messaging kept out of pilot scope.
- [ ] Government mode external pilot only if a specific partner demands it (dual-control enforced).
- [ ] Clinical / therapy packs remain present in code but out of pilot messaging unless explicitly scoped.

---

## Admissibility Requirements Checklist (Quick Reference)

Copy of the living checklist — expand into formal acceptance criteria as items are implemented.

**Language & Epistemic**
- [ ] No forbidden terms anywhere in shipped surface.
- [ ] Forced observed_indicator / non-definitive status at seal.
- [ ] Canonical disclaimer present.

**Gates**
- [ ] Consent + attester before required modes.
- [ ] Training version recorded.
- [ ] Dual-control for government high-priority cues.
- [ ] Prohibited uses blocked.

**Observation Quality**
- [ ] score + model_id + neutral label on every observation.
- [ ] Reproducible under same model versions.

**Package Integrity**
- [ ] Hash/signature at seal.
- [ ] Full gate state + cues + observations exported.
- [ ] No post-seal mutation.

**Human Judgment**
- [ ] Officer notes sealed when present.
- [ ] No automated findings.

**Export & Custody**
- [ ] Durable JSON + PDF (or equivalent).
- [ ] Works with evidence / RMS workflows.

**Docs**
- [ ] Admissibility & Disclosure Guide exists and is accurate.

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
