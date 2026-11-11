# Live Audio and Video Cues — Product Scope

**Product:** CueLiez (Cue + Legal Interview Engine)
**Status:** Product scope, v1, 2026-11-11. Written by the product manager for the engineering design (`docs/design/LIVE_AV_DESIGN.md`, Realtime and Audio Engineer).
**Authority:** Owner decision of 2026-11-11 (`docs/OWNER_DECISIONS.md` section 2a). All earlier locks stand: the never-claim paragraph (section 1), observation-and-cue only, consent plus jurisdiction plus training gates, nothing enabled by default without explicit policy support (`AGENTS.md` section 5), no verdict, no accuracy claims.

This document says what to build and what done looks like. It does not choose speech-to-text engines, models, capture libraries or threading. Those are engineering decisions.

## 0. What exists today and what does not (read from the repo, 2026-11-11)

| Capability | State |
|---|---|
| Per-turn cue loop on NDJSON text turns (`--stream-turns`, `cli.py` `_run_stream_turns`) | Exists. Reruns the observer pipeline over the whole transcript on each turn. |
| Modality gate: `GATED_INPUT_MODALITIES = {audio_features, camera, wearable}`, `record_modality_consent`, `require_gated_modality`, `modality_consents` in gate state | Exists (`gates.py`). No key for microphone capture or speech-to-text. |
| Audio-timing, prosody, visual observers (`gaze_pattern`, `blink_rate`, `motor_activity`) | Exist as observers over caller-supplied features. Not wired to any live source. |
| Microphone or camera capture, speech-to-text, speaker attribution, video feature extraction | Do not exist. |
| Officer indicator of live inputs, kill switch, per-modality records in the sealed package | Do not exist. |

Nothing in this document is built. Every "must" below is a requirement, not a status.

## 1. Product definition

### 1.1 Who uses it
The officer (interviewer) conducting a live interview. CueLiez is an officer assist. The officer decides what, if anything, to ask next. CueLiez never directs the interview, never ends it, and never produces a conclusion.

### 1.2 What the officer sees, and when
One officer-only screen (or panel), shown on a display the subject cannot see:

1. **Live-inputs strip, always visible.** Shows each modality as `ON` or `OFF` with elapsed time and a one-click kill control: `Audio (microphone, speech-to-text, timing)` and, in Phase B, `Video (derived features)`. Details in section 4.3.
2. **Running machine transcript.** Labelled "machine transcript, may contain errors", with speaker role per turn. A turn whose speaker is unconfirmed is shown as unconfirmed (section 3.4).
3. **Cues.** Appear after a turn is finalised (text and timing cues) or after an observation window closes (video cues). Each cue shows its source tag (`text`, `audio timing`, `video-derived`), the quoted turn or the time window, and its caveat line. The officer can acknowledge, dismiss or annotate a cue; those are recorded as human actions.
4. **State messages in place of cues.** "Not enough baseline yet", "tracking quality too low", "input stopped by officer", "input unavailable". The officer must be able to tell silence-because-nothing-to-note from silence-because-the-input-is-down.

### 1.3 What the subject sees and does not see
- The subject does **not** see cues, the transcript view, or the live-inputs strip. This extends the existing subject-not-shown default.
- The subject **is told**, before the interview starts, which inputs are active, through consent form text (section 3.5). Capture does not start until consent is recorded.
- The subject may not be covertly captured. There is no hidden or silent mode.

### 1.4 Modes
| Mode | Live audio/video | Reason |
|---|---|---|
| `generic` | In scope | First-pilot mode. Per-modality consent applies regardless of mode. |
| `interrogation` | In scope | First-pilot mode. Custodial consent questions go to counsel (section 8.1). |
| `government` | Out. Refuse to start live inputs. | Implemented but not a first pilot; dual-control and partner-specific rules unresolved. Revisit only on a named partner. |
| `clinical`, `therapy` | Out. Refuse to start live inputs. | Gaze, blink and movement cues in a health setting read as diagnostic. The owner's locks keep these out of pilot messaging. I recommend they stay out until the owner decides otherwise with counsel. |

The refusal is a gate error recorded like any other gate failure.

### 1.5 Scope exclusions (also policy statements in the consent text and the training addendum)
- Subjects who are minors or who lack capacity: no live audio or video inputs unless counsel approves a specific policy. The officer attests that the subject is an adult with capacity before any live input starts; the attestation is recorded.
- Wearables and physiological inputs: out of this scope.
- Face identification, face recognition, biometric templates, demographic inference, emotion or expression classification: out, permanently, not a phase.

## 2. Phasing

I agree with the lead dev's order (audio, then video as derived features) and make two changes. Phase A is split so the first thing that ships adds the fewest new claims. Phase B has an entry gate, because its grounding is the weakest and the legal questions are the least settled.

### Phase A0 — Live audio to turns (no audio-derived indicators)
**Ships:** microphone capture, local speech-to-text, speaker role attribution, finalised turns fed into the existing stream path, so existing text and consistency cues run on live speech. Consent for `audio_capture`. Live-inputs strip, kill switch, machine-transcript labelling, sealed-package modality record (section 3). Officer sees cues from finalised turns only.
**Does not ship:** any prosody, pitch, or voice-quality feature; any partial-utterance cue.

### Phase A1 — Derived audio-timing features
**Ships:** response latency, speech rate, pause patterns, speaking-time share, derived from the audio timeline, as baseline-relative cues (wording in section 4.2). Separately consent-gated (`audio_features`, existing key) and separately switchable from A0: the officer can run transcription without timing indicators.
**Does not ship:** pitch, jitter, "vocal stress" or any voice-quality indicator. Excluded from live use until a validation plan and a literature review with citations exist (PM action, not scheduled). The existing prosody observers stay off in the live path.

### Phase B — Live video as derived features only
**Entry gate (all required, owner confirms):**
1. Phase A0 and A1 acceptance criteria met and verified by the lead dev.
2. Counsel has answered the video questions in section 8.1 for the pilot jurisdiction.
3. PM literature review of gaze, blink and movement indicators, with cited sources, delivered to the owner. I will not assert what the research shows before that exists.
4. Over-cue measurement on consenting neutral sessions run on Phase A and reviewed by the owner (section 8.2).

**Ships:** local camera capture, in-memory feature extraction for gaze direction (off-camera share), blink rate and overall movement, as baseline-relative, window-based, low-priority cues with a mandatory caveat (section 4.2). Consent for `camera`, separately from audio. Video rules in section 3.
**Does not ship:** stored or transmitted frames; per-frame feature series in the package; emotion, expression, identity or demographic outputs; any use of video-derived indicators as the sole basis for a high-priority cue or for dual-control triggers.

### Not scheduled, listed so nobody builds it by accident
- Retention of raw audio or video by CueLiez (section 3.3 and open question 8.3). The agency's own recording system stays the system of record.
- Wearables. Cloud transcription. Default-on live inputs (the Phase 8 items stay unstarted and need a separate owner decision).

## 3. Hard product rules

These apply to every live modality. Video rules are the strictest; audio follows the same pattern where noted.

### 3.1 Derived features only, in memory
- Video frames are processed in memory and are never written to disk, never stored, and never transmitted off the capture host by default. Only derived numeric features leave the extractor.
- Raw audio follows the same rule: processed in memory for speech-to-text and timing; not written by CueLiez by default.
- The package may hold only: transcript text (as today), derived-feature window aggregates that justify a cue, and process metadata. It never holds pixels, audio samples, face landmarks or embeddings.
- Retained evidence for a video cue is the window aggregate (start, end, value, baseline value, tracking-quality figure), not a per-frame series.

### 3.2 Consent and jurisdiction, per modality, recorded in the gate state
- Each live modality requires its own consent record before capture starts: `audio_capture` (microphone and speech-to-text, new key), `audio_features` (timing indicators, existing key), `camera` (video-derived features, existing key). Each record holds the existing fields (attester, jurisdiction, jurisdiction approved, time) and is part of the sealed gate state.
- Consent for one modality never enables another.
- Consent is mode-independent. The text-only interrogation requirement for consent does not substitute for modality consent.
- Training acknowledgement for live inputs is recorded, naming a training version that covers live audio/video. Without it, live inputs refuse to start.

### 3.3 Retention
- Default: none by CueLiez (section 3.1).
- If the owner ever approves retention of audio or video, it is a separate, explicit opt-in with its own consent record, own text, own retention period and own jurisdiction approval. It is not part of this scope; no code path for it is built in Phase A or B.
- The package may carry a reference (identifier and hash) to a recording held in the agency's own system, supplied by the officer, so a reviewer can tie the sealed record to the recording the agency keeps.

### 3.4 Fail closed, with records
- Missing or incomplete consent, jurisdiction approval, training, attestation, or a disallowed mode: the live input does not start, the capture device is not opened, and the refusal is recorded with its gate error code.
- Input failure mid-interview (device lost, extractor stalled): the strip shows the input as down, cues from that input stop, the interruption is recorded in the package. The interview continues text-only if the officer chooses.
- Speaker role: a turn whose speaker role CueLiez cannot establish is marked `speaker_unconfirmed`, is not used as source text for any cue, and is shown to the officer for confirmation. This repeats the lesson of the therapy-video role defect (ENG-002): unknown speakers must not default to the subject.
- Machine transcript: the package records that turns came from speech-to-text, with component identifier, version, and per-turn confidence where the component gives one. A cue citing low-confidence text carries a flag.

### 3.5 Subject notice (consent form text)
The consent form for each modality states, in plain language: which inputs are active; what is derived from each (text and timing from audio; gaze direction, blink rate and movement from video); that images and sound are processed on local equipment and not stored by CueLiez; that cues go to the interviewer only; that the cues are not findings; and that the subject or the officer can stop an input at any time. Approved wording is jurisdiction-specific and needs counsel. I will draft the base text; counsel approves it before any live session. A session cannot start with text the owner has not approved (the consent form text version is recorded in the package).

### 3.6 Live-inputs indicator
- A persistent strip on the officer screen shows each modality `ON`, `OFF`, `STOPPED BY OFFICER` or `DOWN`, with elapsed time.
- The strip cannot be hidden or collapsed while any input is live.
- The state timeline (start, stop, kill, interruption, each with time and reason code) is recorded in the sealed package.

### 3.7 Kill switch
- One action on the officer screen, and one keyboard shortcut, stops all live inputs. Per-modality stop controls also exist.
- On stop: capture stops, in-memory buffers are discarded, no further cue is generated from that input, the event is recorded with reason code (`officer_stop`, `subject_withdrew`, `fault`). Cues already shown stay in the record.
- A stop is recorded as a human action. It does not end the interview or the session.
- Target: capture stops within 1 second of the action (target until measured).

### 3.8 Not on by default
Live inputs start only when the officer starts them for a session after consent. No pack, config or environment variable turns them on silently.

## 4. Honest-claim guardrails

### 4.1 Position
Audio-timing indicators and video-derived indicators describe how this subject's behaviour in this interview compares with the same subject earlier in the same interview. They are not measures of truthfulness, stress, emotion, intent or credibility. The owner's brief treats the grounding of gaze, blink and movement indicators as weak and culturally variable. This document assumes that and writes the product to it. Before Phase B I will source the research with citations (section 2); until then the product makes no statement about what these behaviours mean.

### 4.2 Allowed wording, by indicator
Every live-input cue has four parts: what changed against the subject's own baseline, the time window, the context caveat, the source tag. Cues name no cause and no state of mind.

Templates (variables in braces). These are the exact shapes engineering implements; strings can change only through the PM.

| Indicator | Cue text template | Caveat line (fixed, shown with every cue of this kind) |
|---|---|---|
| Response delay | `Response delay was {longer|shorter} than earlier in this interview ({value} s against about {baseline} s), around {time}.` | `Delays have many ordinary causes, such as recall effort, question difficulty or audio lag. Audio timing.` |
| Speech rate | `Speech rate was {higher|lower} than earlier in this interview ({value} against about {baseline} words per minute) between {start} and {end}.` | `Speech rate varies with topic, language and comfort with the setting. Audio timing.` |
| Pause pattern | `Pauses within answers were {more|less} frequent than earlier in this interview between {start} and {end}.` | `Pauses have many ordinary causes. Audio timing.` |
| Off-camera gaze | `Gaze was directed away from the camera {more|less} often than earlier in this interview between {start} and {end}.` | `Gaze habits vary by culture, comfort, disability and where the camera sits relative to the screen. Video-derived, low confidence.` |
| Blink rate | `Blink rate was {higher|lower} than earlier in this interview between {start} and {end}.` | `Blink rate varies with fatigue, lighting, dry eyes and contact lenses. Video-derived, low confidence.` |
| Movement | `Overall movement was {higher|lower} than earlier in this interview between {start} and {end}.` | `Movement varies with posture, seating and room conditions. Video-derived, low confidence.` |
| Not enough data | `Not enough baseline yet for {indicator}.` / `Tracking quality too low for {indicator}.` | none |

Rules the cue text must follow:
- **Own-baseline only.** The comparison is to the same subject earlier in the same interview. Never to a population, other subjects, or a "normal" range.
- **Baseline required.** No shift cue until a minimum baseline window exists and tracking or transcription quality passes a threshold. The window length is a target to be set by measurement (proposal to start from: the first two minutes of rapport questions); below it, the "not enough baseline" state shows.
- **Coincidence, not response.** A cue may list the question under way in its window as context ("during the question about ..."); it never says "in response to" or "when asked about".
- **No probe from video.** Video-derived and audio-timing cues do not propose a topic to press. They may say `Consider whether a break or rewording of the question would help.`
- **Priority ceiling.** Video-derived cues are capped at the lowest priority tier. Audio-timing cues are capped at medium. Neither can on its own raise a high-priority cue or trigger dual-control. Text-based inconsistency cues keep their existing priorities.
- **Separate sections.** In the officer screen and in the sealed package, video-derived and audio-timing indicators are labelled by source and not merged into the ranking of text inconsistency cues.
- **Rate limit.** At most one cue per indicator per window, and a ceiling on live-input cues per ten minutes (target to be set after the over-cue measurement).

### 4.3 What the product may never say
Not in cue text, labels, observation keys, UI, exports, training, sales material or demos:
- Any word naming an inner state or intent: nervous, anxious, stressed, tense, uncomfortable, evasive, avoiding, hiding, guarded, suspicious, deceptive, truthful, sincere, confident, defensive.
- "Tell", "micro-expression", "stress indicator", "deception indicator", "lie indicator", "credibility", "reliability" (of a person), "red flag".
- Any statement of accuracy, hit rate, or that the signal reflects truthfulness.
- Any emotion or expression label from video.
- "Aversion" for gaze. It implies a motive. The existing visual observer cue text uses "gaze aversion ratio" (`observations/visual.py`, gaze indicator). It must read "off-camera gaze" before any live use (ENG-007).

The seal-time language gate must reject these terms in live-input labels and cue text (it does not today for verdict terms; see the independent review in `DIARY.md`).

### 4.4 Language compliance run
The strings in section 4.2 and the notice in section 3.5 were run through the language-compliance skill. Result recorded in `DIARY.md` entry of 2026-11-11 (live AV scope).

## 5. Deployment constraints
- On-prem or private cloud, per `docs/OWNER_DECISIONS.md` section 3. Speech-to-text and video feature extraction run on the capture host or in the customer's own environment.
- No cloud transcription by default and no outbound call of any kind for audio or video content. A customer may point CueLiez at a transcription service inside their own private environment by explicit configuration; that choice is recorded in the package.
- The core package stays dependency-free. Capture libraries, speech-to-text and video models are optional extras, installed separately. The base install, its tests and its CI keep working with none of them.
- Model identifiers, versions and checksums of the speech-to-text and video extractors are recorded in the sealed package.
- Reference hardware for latency targets is chosen by the engineer and written into the measurement report.

## 6. Acceptance criteria

Latency and quality numbers below are targets until the engineer measures them on stated reference hardware; the measurement report must say so. A criterion with a number is not met by code review; it is met by a recorded run.

### Phase A0 (live audio to turns)
1. **Consent refusal.** Given no `audio_capture` consent, when the live-audio stream is started, then it exits with the gate error code, the capture source is never opened, and the refusal is in the audit record. Verify: test with a fake capture source asserting zero opens.
2. **Mode refusal.** Given `therapy`, `clinical` or `government` mode with full consent, when live audio is started, then it refuses with a recorded gate error.
3. **Spoken fixture.** Given a 2-minute recorded fixture with two speakers (owner synthetic script, played into the capture source), then turns are produced with speaker roles, and the first cue appears within 5 seconds (target) of the end of the triggering utterance, with the measured value reported.
4. **Cue source.** Every cue from live audio cites a finalised turn. No cue cites a `speaker_unconfirmed` turn or an empty-text turn.
5. **Machine transcript record.** Given a sealed live session, then the package holds the speech-to-text component id and version, the consent record for each live modality, and a state timeline (start, stop, interruptions) inside the hashed area, and `--verify-package` passes on the exported file.
6. **Kill switch.** Given a running session, when the officer triggers stop, then capture stops within 1 second (target), the event is in the timeline with a reason code, no further audio cue is produced, and the session can still seal.
7. **No audio at rest.** Given a full run, then no audio file exists under the output directory or temp directory created by CueLiez, and the package contains no audio samples. Verify: test diffing the directories.
8. **Offline.** Given network access blocked, the run completes. Verify: test with sockets patched to fail.
9. **Dependency-free core.** Given an install without the audio extra, the existing test suite passes and the live command exits with a clear error naming the missing extra.
10. **Subject not shown.** Given the officer surface, then the subject-not-shown notice and the live-inputs strip are present, and the strip cannot be hidden while input is live.

### Phase A1 (audio-timing features)
1. **Separate switch.** Given `audio_capture` consent without `audio_features` consent, then transcription runs and no timing cue is produced, and the strip shows timing `OFF`.
2. **Baseline rule.** Given a fixture with a shift before the baseline window completes, then the officer sees "Not enough baseline yet" and no shift cue.
3. **Wording.** Given any timing cue, then the text matches a template in section 4.2 and carries its caveat line; a test fails on any other text. The language check passes on every template.
4. **Priority ceiling.** Given a fixture with a large shift, then the highest priority of a timing cue is the medium ceiling, and no dual-control record is demanded by a timing cue alone.
5. **Reproducible.** Given the same fixture twice, then the same timing features and cues result, with the tolerance stated by the engineer.

### Phase B (video as derived features)
1. **Consent refusal.** Given no `camera` consent, the stream refuses, the camera is never opened, the refusal is recorded.
2. **No frames at rest or on the wire.** Given a 2-minute video fixture, then no image or video file is created by CueLiez, no outbound connection is attempted, and the package contains only whitelisted numeric aggregates. Verify: directory diff, patched sockets, package schema check.
3. **Per-modality switch.** Camera can be stopped while audio continues, and the reverse; each is recorded.
4. **Tracking quality.** Given a fixture with the face out of view or in poor light, then the officer sees "Tracking quality too low" and no shift cue.
5. **Wording and ceiling.** As Phase A1 criteria 3 and 4, for the three video templates, at the lowest-priority ceiling. No forbidden term from section 4.3 appears in any label, key or string (scan of `src/` live-video strings plus package).
6. **Indicator.** Given video on, then the strip shows `Video ON` from the first frame processed to the stop event, and the timeline in the package matches.
7. **No forbidden outputs.** The extractor output schema has no emotion, expression, identity or demographic field. Verify: schema test.
8. **Over-cue measurement.** Given at least 10 consenting neutral sessions, then the engineer reports video cues per ten minutes per indicator, and variation across stated conditions (lighting, glasses, camera position). The owner reviews the report before any operational use.

## 7. Phase 7 and 8 roadmap effect
`TODO.md` Phase 7 items for real-time audio hooks and visual observers stay `[ ]` and are reworded to point to this scope. The Phase 8 default-on items stay `[ ]`; this decision makes live inputs available per session after consent and does not make them default. Default-on would need its own owner decision (open question 8.7).

## 8. Open questions for the owner, with recommendations

1. **First live context.** Real subjects, or consenting participants in training exercises first? Recommend: training exercises and consenting volunteers for all of Phase A, and for Phase B until the over-cue report is reviewed. This matches section 2 of `OWNER_DECISIONS.md` (training context or one unit) and lets us measure without a real case depending on the result.
2. **Interview-room reality.** Who confirms speaker roles? Recommend: two-channel capture (one microphone per speaker) where the site can do it; otherwise the officer confirms roles at the start and any unconfirmed turn is flagged.
3. **Raw audio or video retention.** Build an opt-in at all? Recommend: not in Phase A or B. CueLiez references the agency's own recording by hash. Revisit only if a partner asks, with counsel.
4. **Retaining derived video indicators in the sealed package.** Keep or discard on seal? Recommend: keep, labelled, because discarding what the officer saw creates a gap between the interview and its record. Needs counsel.
5. **Consent text ownership.** Recommend: PM drafts the base text, counsel approves per jurisdiction, version recorded in the package.
6. **Cloud transcription.** Recommend: none in v1. A customer's own private environment only, by explicit configuration.
7. **Phase 8 default-on items for audio and camera.** Recommend: strike camera default-on, and keep audio default-on as an open item needing its own decision. Live video should never be on without the officer starting it.
8. **Therapy, clinical, government.** Recommend: refuse live inputs in these modes (section 1.4). Confirm.
9. **Pilot partner statements.** Recommend: no external description of live video until Phase B passes its gate; Phase A may be described, in language that passes `LANGUAGE_RULES.md`, after owner review.
10. **Minors and persons lacking capacity.** Recommend: out, with officer attestation recorded (section 1.5). Confirm.

## 9. Risks

### 9.1 Legal — needs counsel, no conclusions here
- **Consent and recording law.** Rules on recording or analysing audio and video differ by jurisdiction, including who must consent. The set for the first pilot jurisdiction must come from counsel.
- **Voluntary consent in custody.** Whether consent captured in a custodial interview is treated as voluntary, and what the form must say. Counsel.
- **Biometric and face-derived data.** Whether features derived from a face image (gaze, blink, movement), even if never stored, fall under biometric or privacy statutes in the pilot jurisdiction. Counsel.
- **Admissibility and disclosure.** How a record containing video-derived indicators is treated for disclosure, and whether it opens challenges to the whole package. `docs/ADMISSIBILITY_AND_DISCLOSURE.md` has not been updated for live inputs; it needs a counsel-reviewed update before Phase B.
- **Machine transcription as record.** Whether a machine transcript used for live cues needs a certified or reviewed version for later use. Counsel.
- **Notice duties.** Whether the interviewee, interpreter, defence or other attendees must be told or must consent separately. Counsel.

### 9.2 Bias and over-cue
- Baseline-relative shifts still vary across individuals, cultures, disabilities, glasses, head coverings, camera angle and lighting. The product cannot show equal behaviour across these groups; it can measure cue rates under stated conditions (Phase B criterion 8) and must publish what it cannot establish.
- Automation bias: officers may give machine cues more weight than they deserve. Mitigations in the design: priority ceilings, mandatory caveat, own-baseline wording, separate sections, rate limits, and a training addendum for live inputs (PM drafts; recorded as the training version in the gate state).
- Speech-to-text may drop or normalise disfluencies and mishear accents, names and languages other than the model's strongest. Text observers that depend on hedges or fillers may be skewed. The engineer must report which observers are affected and the product must flag low-confidence text (section 3.4).

### 9.3 What would make me pull a modality
Any one of these pulls the modality back to off, pending owner decision:
- A pilot user, partner or reviewer describes a live-input cue as showing deception, stress or credibility, and the correction does not hold in training.
- Counsel advises against it for a jurisdiction (that jurisdiction only).
- The over-cue report shows video cue rates that differ materially across lighting, glasses or camera-position conditions and the engineer cannot reduce the difference. The owner sets the threshold; I will not invent one.
- A recorded case of frames, audio samples or face-derived vectors found at rest or on the wire.
- Cue use in the interview materially disrupts it, as reported by pilot officers.
- Speech-to-text word error on pilot speech is too high for officers to rely on cue sources. The pilot officers define the threshold.
