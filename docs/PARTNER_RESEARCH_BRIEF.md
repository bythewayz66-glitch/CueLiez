# Partner Research Brief — CueLiez (1 page)

**Product:** CueLiez (Cue + Legal Interview Engine) — real-time signal observation and testimony cues for legal interviews. Not a lie detector.

**Contact / owner:** Product owner (human). Technical: see repository `bythewayz66-glitch/CueLiez`.

---

## What CueLiez does

CueLiez observes selected behavioural and linguistic signals and testimony inconsistencies in interview material and surfaces neutral cues so a trained human can decide what, if anything, to probe or clarify. It does not detect lies, measure truthfulness, score credibility, diagnose conditions, or determine guilt or innocence.

Sealed outputs are **observed indicators and process metadata** for human review — not findings, not evidence of deception, and not a substitute for judgment, policy, or law.

## What we are asking for

A small, low-risk controlled study with 1–2 investigative-interviewing research groups or training contexts, using **synthetic and de-identified transcripts only** (no real case data in early phases). Study questions:

1. Do officers find the cues useful for follow-up questions?
2. What is the over-cue / false-positive rate on clean accounts?
3. Does the sealed package (observations, cues, gate state, hash) support review and disclosure?
4. Does the process preserve human judgment as the final step?

## What we provide

- Synthetic + de-identified transcript sets (owner demo transcripts + red-team fixtures).
- The CueLiez CLI and sealed-package artifacts (JSON + human-readable summaries) for reproducible analysis.
- Gate state, consent/training/dual-control records, disclaimer, and package hash in every sealed package.
- Full test suite (366+ tests) and documentation (language rules, admissibility guide, observer inventory).

## What we do not claim

- No accuracy of deception detection.
- No confession-rate improvement.
- No automated legal, clinical, or credibility findings.
- No diagnostic or medical-device positioning.

## Data handling

- On-prem / private-cloud processing preferred; no public SaaS required for v1.
- Synthetic/de-identified transcripts only in early phases; no real case data.
- Sealed packages treated as observation artifacts, not findings.

## Suggested study design (low risk)

- Within-subject or A/B on synthetic transcripts.
- Measure: cue utility (officer-rated), over-cue rate on clean accounts, package completeness, gate compliance, latency.
- IRB/ethics review with the partner institution.

## Guardrails

- Authorship, data ownership, and publication terms agreed in advance.
- All external claims ≤ the never-claim paragraph (`docs/OWNER_DECISIONS.md` §1).
- Position as: clearer inquiry + auditable record of observations and cues, fairer and tighter for both the guilty and the innocent.

## Contact

Product owner (human). Repository: `bythewayz66-glitch/CueLiez`. All materials subject to `AGENTS.md` and `docs/LANGUAGE_RULES.md`.