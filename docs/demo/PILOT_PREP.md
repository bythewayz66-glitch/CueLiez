# CueLiez Pilot Prep (v1, docs outline)

**Scope:** first pilot preparation for `generic` + `interrogation` modes only. Observation/cue framing only; never stronger than the locked never-claim paragraph in `docs/OWNER_DECISIONS.md`.

## Pilot context (owner-aligned)

- **Primary modes:** `generic` + `interrogation` only. Government/clinical/therapy not first-pilot messaging/deployment unless specifically required by an approved partner decision.
- **User profile:** internal demo → one investigative interviewing training context or a single detective unit that already records interviews.
- **Deploy posture:** on-prem or private-cloud processing of interview text/transcripts; no public SaaS required in v1.
- **Success criteria (non-accuracy):** officers find cues useful for follow-up questions; packages seal with gates; the tool is never framed as lie detection. Do not measure or claim truth-detection accuracy or automated outcomes.

## Interviewing practice framing (PEACE / cognitive interviewing)

CueLiez is an **interview-support** layer that may help trained professionals notice patterns worth clarifying. It does **not** replace PEACE, cognitive interviewing, local policy, or professional judgment.

- Use cues as prompts to **plan/probe/clarify** (e.g., ask for specifics, verify timelines, invite elaboration) within lawful, ethical, and agency-approved interviewing methods.
- Cues are probabilistic observed indicators, not findings. They must not be used as evidence of deception, guilt, innocence, or credibility.
- Operators remain responsible for consent, recording, disclosure, documentation, and adherence to applicable interviewing standards and jurisdictional requirements.

## Operator certification / training program outline (docs only)

A formal certification program is not implemented in code here; this is a documentation outline for pilot readiness.

1. **Language and limits:** never-claim paragraph, `docs/LANGUAGE_RULES.md`, prohibited uses (no lie-detector framing, no automated legal/clinical decisions, no diagnosis).
2. **System behavior:** observations/cues, confidence/model metadata, source transcript quotes as evidence context, insufficient-data/no-cue states.
3. **Gates and process:** consent/attestation, training acknowledgement/version, mode requirements, dual-control where applicable (government mode not first-pilot default).
4. **Package handling:** sealed JSON as canonical artifact, `package_hash` integrity meaning (recorded observations/process, not proof of subject claims), officer notes (human) vs system cues, export/review workflow.
5. **Pilot exercises:** run owner synthetic transcripts and local de-identified/approved materials; record over-cue/under-cue and follow-up usefulness observations (`docs/demo/VALIDATION_NOTES.md`); never score deception accuracy.
6. **Escalation:** stop and document if outputs are misused as findings or if scope conflicts with `docs/OWNER_DECISIONS.md`.

## Positioning and pricing guidance (no accuracy claims)

- **Allowed positioning:** clearer inquiry, structured follow-up prompts, auditable observation/cue records, gate-aware process support for trained humans.
- **Not allowed:** accuracy-of-deception claims, confession-rate improvement claims, truth/credibility scoring, automated detention/charge/clearance decisions, clinical/diagnostic claims, polygraph-substitute marketing.
- **Pricing experiments (if pursued):** must match positioning (e.g., per-seat/per-session or on-prem support tiers) and must not be tied to deception-detection accuracy or automated outcomes. Any external copy must be weaker than or equal to the never-claim paragraph.