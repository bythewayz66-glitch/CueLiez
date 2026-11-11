# Owner Decisions — CueLiez

**Authority:** Product owner (human). Agents must not invent conflicting policy.
**Last updated:** 2026-11-11

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
