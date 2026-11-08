# TODO.md — Agent-Readable Task List for CueLiez

**Goal:** Turn CueLiez into a production-ready, compliance-first interview-assist layer that supports both **credibility** and **admissibility**, with a realistic path toward becoming a standard integration target (Axon, CaseCracker, RMS, etc.) in the $50–150M+ ARR range long-term.

All work must obey `AGENTS.md` and `docs/LANGUAGE_RULES.md`.

Status key: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Phase 0 — Stabilize the Skeleton (Immediate, 2–4 weeks)

- [ ] Add minimal real dependencies to `pyproject.toml` (pydantic for schemas, numpy/scipy or equivalent for basic signal features, keep pytest).
- [ ] Ensure default and full observation runners produce usable output on sample transcripts.
- [ ] Make GitHub Pages live; ensure landing page and docs emphasize “Not a lie detector”.
- [ ] Create a simple CLI or notebook that accepts transcript JSON → emits sealed package + cue list.
- [ ] Confirm language tests and gate tests pass on current main.
- [ ] Version the canonical disclaimer and reference it from seal path and docs.

---

## Phase 1 — Production-Grade Observers (1–3 months)

- [ ] Keep existing heuristic/rule observers as the fast, explainable baseline.
- [ ] Layer lightweight ML / LLM-assisted observers for high-value signals (hedging, pronoun distancing, detail vagueness, claim conflicts, timeline inconsistency) behind feature flags or model_id versioning.
- [ ] Ensure every observer emits gate-compatible observations (score + model_id + neutral label).
- [ ] Add confidence calibration and explicit “insufficient data” / no-cue states.
- [ ] Document model versions and provenance for every observer that is not pure rule-based.
- [ ] Expand test coverage for new observers (neutral labels, confidence bounds, no verdict language).

---

## Phase 2 — Gated Modalities & Real-Time Delivery (2–4 months)

- [ ] Keep feature / physiological / visual observers gated; do not enable by default in packs.
- [ ] Build explicit consent + jurisdiction checks before enabling audio feature extraction or any camera/wearable input.
- [ ] Prioritize audio-only real-time path first (prosody, speech rate, latency, pause patterns).
- [ ] Implement officer-facing delivery (onscreen overlay / tablet cues) that the subject does not see by default.
- [ ] Add optional officer response / note field for high-priority cues; include it in the sealed package.
- [ ] Target end-to-end latency < 1–2 seconds for text cues on local or private-cloud instance.

---

## Phase 3 — Admissibility Hardening (Parallel, start immediately)

### 3.1 Language & Epistemic Status
- [ ] Audit all code, docs, UI strings, and package fields for forbidden terms.
- [ ] Force `epistemic_status = "observed_indicator"` and `is_definitive_finding = false` at every seal.
- [ ] Embed canonical disclaimer in every sealed package.
- [ ] Reject banned annotation keys and verdict labels at seal time (already partially present — complete and test).

### 3.2 Consent, Training, Dual-Control Capture
- [ ] Ensure full gate state (consent attester + timestamp, training version, dual-control records, intended uses) is serialized into the sealed package.
- [ ] Make consent / training / dual-control failures produce clear, auditable GateError codes.
- [ ] Add tests that prove packages cannot be sealed without required gates in high-stakes modes.

### 3.3 Package Integrity & Export
- [ ] Define and implement a stable sealed-package schema (JSON) that includes observations, cues, gate state, disclaimer, product/version, seal timestamp, session identifiers.
- [ ] Add cryptographic hash (and later signature) of the package at seal time.
- [ ] Provide durable export formats: signed/structured JSON + human-readable PDF.
- [ ] Prevent post-seal mutation of observations or epistemic fields.

### 3.4 Human Judgment Preservation
- [ ] Officer action/note field for high-priority cues is optional but sealed when present.
- [ ] Package never records automated legal, clinical, or credibility findings.
- [ ] Clear separation in schema and docs between “system observed/suggested” and “human decided”.

### 3.5 Documentation for Disclosure
- [ ] Write first version of **Admissibility & Disclosure Guide** (what is/isn’t in the package, how consent/training/dual-control appear, recommended disclosure handling).
- [ ] Keep sales, training, and UI language consistent with technical reality.
- [ ] Prepare short internal validation notes (false-positive / over-cue rates, officer utility) that do **not** claim truth-detection accuracy.

---

## Phase 4 — Privacy, Security, Integration

- [ ] Design primarily for on-prem / air-gapped / private-cloud deployment (CJIS / equivalent readiness).
- [ ] Document data-retention and access controls for sealed packages.
- [ ] Integration priority order:
  1. Transcript ingest from existing systems (Axon, CaseCracker, etc.)
  2. Real-time audio stream hooks
  3. Officer UI (tablet overlay or simple web dashboard)
  4. Export into RMS / case / evidence management systems
- [ ] Make sealed packages easy to attach as original artifacts rather than derivative interpretations.

---

## Phase 5 — Validation & Evidence of Value

- [ ] Build private red-team / synthetic + de-identified transcript set for regression and utility testing.
- [ ] Partner with 1–2 academic or practitioner groups in investigative interviewing for small controlled studies (officer follow-up quality, review usefulness, over-cue rates).
- [ ] Target early pilot agencies that already record interviews and care about PEACE / cognitive interviewing standards.
- [ ] Measure and report latency, completeness of packages, and gate compliance in pilots.

---

## Phase 6 — Go-to-Market & Commercial

- [ ] Pricing experiments that match positioning (per-seat / per-session SaaS or on-prem + support; higher tiers for government dual-control and multi-modality).
- [ ] Productize existing training gates into an operator certification / training program.
- [ ] Explore partnerships with interview-room hardware and evidence-platform vendors.
- [ ] Never market accuracy-of-deception, confession rates, or automated decisions.
- [ ] Primary message: clearer inquiry + auditable record of observations and cues, fairer and tighter for both the guilty and the innocent.

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
