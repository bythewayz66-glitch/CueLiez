# Owner Decisions — CueLiez

**Authority:** Product owner (human). Agents must not invent conflicting policy.
**Last updated:** 2026-11-08

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
| **Physiological / visual / wearable** | Remain **off by default**; not in pilot |
| **First user profile** | Internal demo → one investigative interviewing training context or a single detective unit that already records interviews |
| **Success for pilot** | Officers find cues useful for follow-up questions; packages seal with gates; no one describes the tool as a lie detector |

---

## 3. Deploy posture (v1)

- Prefer **on-prem or private-cloud** processing of interview text/transcripts.
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
