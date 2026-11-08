# CueLiez

**CueLiez** (Cue + **L**egal **I**nterview **E**ngine) is a system for real-time **signal observation** and **testimony cues** in legal interviews.

It is **not** a lie detector. It does not detect lies. It observes behavioural and linguistic signals and inconsistencies in testimony, and presents them to the officer so the interview can be more meaningful for both the guilty and the innocent.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Site](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://bythewayz66-glitch.github.io/CueLiez/)

## 10-second pitch

CueLiez cues officers in legal interviews with real-time signal and testimony-consistency observations—never lie verdicts—and seals an auditable record so inquiry is sharper for the guilty and fairer for the innocent.

## GitHub Pages (enable once)

Direct link to flip the switch:

**https://github.com/bythewayz66-glitch/CueLiez/settings/pages**

Set **Source** → **GitHub Actions** → Save. Then the site deploys to https://bythewayz66-glitch.github.io/CueLiez/

## The system (not a subsystem)

CueLiez is a standalone product system. It incorporates:

- A **trusted memory substrate** (grounded vs simulated partitions; contamination controls; sealed observed indicators)
- A **Legal Interview Engine** layer: live/session observation, cues to the officer, hard gates (consent, training, dual-control, prohibited uses)

Heritage: patterns from [mem20-ce](https://github.com/bythewayz66-glitch/mem20-ce) and the former mem20liez organ in [mem20](https://github.com/bythewayz66-glitch/mem20). In this repository, CueLiez **is** the system.

## Language rules

Mandatory vocabulary and bans (including **lie detector**): see [docs/LANGUAGE_RULES.md](docs/LANGUAGE_RULES.md). Locked never-claim framing and pilot scope: [docs/OWNER_DECISIONS.md](docs/OWNER_DECISIONS.md).

## Mission

See [MISSION.md](MISSION.md).

## What officers get

- Real-time **cues** when stress-related signals, linguistic patterns, or testimony conflicts appear
- Suggestions on how to probe or clarify — not machine verdicts
- A **sealed session package** of observed indicators with confidence, model identity, and disclaimers
- Policy gates so high-stakes modes cannot silently skip consent, training, or dual-control

## What CueLiez refuses

- Automated detention, charge, or clearance decisions
- Definitive deception claims
- Clinical diagnosis or medical-device positioning
- Polygraph-substitute marketing or use
- Covert use without lawful authority

## 26-second investor description

See [docs/PITCH_26S.md](docs/PITCH_26S.md).

## Layout

```
CueLiez/
├── MISSION.md
├── LICENSE                 # Apache-2.0
├── docs/
│   ├── LANGUAGE_RULES.md
│   ├── PITCH_26S.md
│   └── ...
├── src/cueliez/            # System package
├── docs/site/              # GitHub Pages
└── assets/logo.svg
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
