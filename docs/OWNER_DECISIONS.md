# Owner Decisions — CueLiez

**Authority:** Product owner (human). Agents must not invent conflicting policy.
**Last updated:** 2026-11-25 (section 2b: reversal of the permanent exclusions, separate demographic gate, real face recognition)

---

## 1. Never-claim paragraph (locked)

CueLiez does not detect lies, measure truthfulness, score credibility, diagnose conditions, or determine guilt or innocence. It observes selected behavioural and linguistic signals in interview material and surfaces neutral cues so a trained human can decide what, if anything, to probe or clarify. Sealed outputs are observed indicators and process metadata for human review—not findings, not evidence of deception, and not a substitute for judgment, policy, or law.

Use this paragraph (or a strict paraphrase that does not soften it) in README, demos, training, and any external description.

---

## 2. First pilot scope

| Decision | Choice |
|----------|--------|
| **Primary modes for first pilot** | `generic` + `interrogation` only |
| **Government mode** | Implemented and tested, but **not** the first external pilot unless a specific partner demands it |
| **Clinical / therapy packs** | Present in code; **out of scope** for first pilot messaging and deployment |
| **Physiological / visual / wearable** | Remain **off by default**; not in pilot. **Superseded in part for visual input by section 2a (2026-11-11).** Wearable and physiological input stay out. |
| **First user profile** | Internal demo → one investigative interviewing training context or a single detective unit that already records interviews |
| **Success for pilot** | Officers find cues useful for follow-up questions; packages seal with gates; no one describes the tool as a lie detector |

## 2a. Live audio and video input (owner decision, 2026-11-11)

**Decision (relayed by the lead dev, from the product owner):** "CueLiez will give cues during a LIVE interview from live AUDIO and live VIDEO inputs, not only text transcripts."

**What it supersedes:** the section 2 row that kept visual/physiological input out of the first pilot and off by default, for audio and video input only. Before this decision CueLiez took text turns only (`--stream-turns` over NDJSON); there was no capture, speech-to-text or video feature extraction.

**What stays locked, unchanged:** the never-claim paragraph (section 1); observation-and-cue only; consent, jurisdiction and training gates; nothing enabled by default without explicit policy support (`AGENTS.md` section 5); no verdict language and no accuracy claims; wearable and physiological input stay out; on-prem or private-cloud processing (section 3).

**Product scope and phasing:** `docs/design/LIVE_AV_PRODUCT_SCOPE.md` (live audio first, then live video as derived features only, each separately consented and separately switchable; frames never stored or transmitted by default; kill switch and a visible live-inputs indicator). Phase A and Phase B are not built; Phase B has an entry gate in that document. Items in that document marked as open questions are not owner decisions until the owner answers them.

## 2b. Reversal of the permanent exclusions (owner decision, 2026-11-25)

**Decision (directly from the product owner):** the earlier "permanently excluded" list is reversed. The following are now enabled — **as gated, consent-required, jurisdiction-checked features, never on by default silently, never as definitive findings**:

- face identification / recognition
- biometric templates
- demographic inference
- emotion / expression classification
- wearables / physiological input
- pitch / voice-quality features
- cloud transcription (gated opt-in only, no provider bundled, never by default)

**What stays locked, unchanged:** the never-claim paragraph (section 1); observation-and-cue only; sealed packages remain `observed_indicator` / `is_definitive_finding=false`; dishonesty signs are probabilistic indicators for human review, never verdicts or guilt findings.

**Demographic inference — its OWN separate gate (clarified 2026-11-25 20:00 MST):** demographic inference stays behind a separate opt-in, a separate consent record, and a separate bias/admissibility warning in code and docs. It is high-risk, bias-prone, and admissibility-sensitive. General modality consent (camera/audio/wearable) or a state-wide jurisdiction approval NEVER enables it. The observer only reports caller-supplied attributes, with a low score ceiling and a bias caveat; no demographic classifier is built.

**Face recognition — REAL, not a placeholder (clarified 2026-11-25 20:00 MST):** enrollment + matching with real embeddings and distances and a confidence score, tested end-to-end with real images. Implementation: OpenCV Haar-cascade detection, FacemarkLBF 68-point alignment, OpenFace `nn4.small2.v1.t7` 128-d embeddings, Euclidean distance, threshold 0.9 (measured on a 5-photo public-domain fixture — deployments must calibrate their own threshold). Optional extra `cueliez[face]` (`opencv-contrib-python-headless==4.10.0.84`); core stays dependency-free. Gated behind face-rec consent + jurisdiction. Biometric templates are sensitive data: stored only with explicit consent, in-memory by default, with deletion (`delete_subject` / `delete_all`), documented retention/deletion, never transmitted by default.

**Other decisions in the same instruction (2026-11-25):** fix the sealed-package hash verify bug; add more dishonesty-sign observers (text/audio/visual/context); make the 9 feature observers work properly; add narrative observers to runners; turn ALL observers on by default in runners and packs (text observers by default; feature/gated observers included in the lists but firing only with feature metadata + consent); implement ML/assisted observers behind explicit opt-in; build the live AV surface (Phase 10 A0/A1/B); fix dashboard XSS, modality-consent gaps, and malformed NDJSON in `--stream-turns`; build a real web frontend (`--web`) that actually operates the pipeline.

---

## 3. Deploy posture (v1)

- Prefer **on-prem or private-cloud** processing of interview text/transcripts. Live audio and video (section 2a) follow the same rule: speech-to-text and video feature extraction run locally or in the customer's own environment; no cloud transcription by default.
- No requirement for public SaaS in v1.
- Sealed packages treated as **artifacts that attach to a case/evidence workflow**, not as automated decisions.
- Live Axon / CaseCracker / RMS **integrations are post-pilot** unless a pilot partner already supplies transcript export only.

---

## 4. Demo materials agents should prefer

Owner-supplied / preferred examples live under:

- `docs/examples/owner_clean_interview.json`
- `docs/examples/owner_conflict_interview.json`
- `docs/examples/owner_hedging_interview.json`

These are **fully synthetic**. They are for regression, CLI dry-run, and human judgment of cue quality—not real cases.

**What “good” looks like for the owner:** cues suggest probes or clarifications a careful interviewer might already consider; they do not assert what happened.

---

## 5. Admissibility doc posture (owner read)

`docs/ADMISSIBILITY_AND_DISCLOSURE.md` v1 is **accepted as directionally correct** for technical framing (non-finding, gates, hash, officer notes). Owner expectations:

- Do not let export or CLI wording drift stronger than this doc.
- Any sales one-pager must be weaker or equal—never stronger—than the never-claim paragraph above.
- Hash verification story must stay “integrity of recorded observations/process,” never “proof the subject lied.”

---

## 6. Standing instructions to agents

- Obey `AGENTS.md`, `LANGUAGE_RULES.md`, and this file.
- First pilot features > speculative modalities.
- If a task conflicts with these decisions, stop and note in `agent_notes/` rather than expanding scope.
