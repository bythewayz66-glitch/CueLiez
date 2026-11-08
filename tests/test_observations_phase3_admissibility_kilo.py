"""Phase 3 (admissibility hardening, kilo): language, bounds, insufficient-data, contract, reproducibility.

Observer surface checks are neutral and observation-only (no verdict/deception findings).
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from cueliez.observations import default_runner, full_runner
from cueliez.observations.base import FORBIDDEN_LABELS
from cueliez.observations.behavioral import (
    AnswerLengthVarianceObserver, EvasionMarkerObserver, FilledPauseMarkerObserver,
    InterruptionOverlapObserver, ResponseLatencyObserver, SpeechRateShiftObserver,
)
from cueliez.observations.consistency import (
    ClaimConflictObserver, DetailDriftObserver, LocationReferenceDivergenceObserver,
    SelfReferenceShiftObserver, TimelineInconsistencyObserver,
)
from cueliez.observations.linguistic import (
    CertaintySwingObserver, DetailVaguenessObserver, HedgingObserver, MemoryQualifierObserver,
    MinimizationObserver, NegationDensityObserver, OverjustificationObserver,
    PassiveVoiceProxyObserver, PronounDistancingObserver,
)

ROOT = Path(__file__).resolve().parents[1]

ALL_OBSERVERS = [
    HedgingObserver, PronounDistancingObserver, NegationDensityObserver, DetailVaguenessObserver,
    CertaintySwingObserver, MinimizationObserver, PassiveVoiceProxyObserver, OverjustificationObserver,
    MemoryQualifierObserver, ClaimConflictObserver, TimelineInconsistencyObserver, DetailDriftObserver,
    LocationReferenceDivergenceObserver, SelfReferenceShiftObserver, ResponseLatencyObserver,
    AnswerLengthVarianceObserver, EvasionMarkerObserver, SpeechRateShiftObserver,
    FilledPauseMarkerObserver, InterruptionOverlapObserver,
]

FORBIDDEN_TEXT = re.compile(
    r"\b(lie\s+detector|detects?\s+lies?|lie\s+detection|truth\s+detector|truth\s+score|"
    r"proves?\s+deception|confirms?\s+(?:lying|deception)|subject\s+is\s+lying|"
    r"\bguilty\b|\bdeception_confirmed\b|polygraph)\b",
    re.I,
)

REPRESENTATIVE = [
    {"role": "subject", "text": "I think maybe I was around there doing stuff, sort of."},
    {"role": "subject", "text": "I did not take it. I was at eight and then at nine."},
    {"role": "subject", "text": "I don't remember exactly; it was later, I guess."},
    {"role": "subject", "text": "I got there at 9:00 pm and left at 10:30 pm."},
    {"role": "subject", "text": "No, I never went in. Well, I went in briefly."},
]


def _load_fixture(name: str):
    for base in (ROOT / "docs" / "examples", ROOT / "tests" / "fixtures", ROOT / "tests" / "fixtures" / "transcripts"):
        p = base / name
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(name)


class TestPhase3AdmissibilityKilo(unittest.TestCase):
    def _assert_contract(self, o):
        label = str(o.get("label") or "")
        self.assertTrue(label.strip(), "empty label")
        self.assertNotIn(label.lower(), FORBIDDEN_LABELS, label)
        conf = o.get("confidence") or {}
        score = conf.get("score")
        self.assertIsInstance(score, (int, float))
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertTrue(str(conf.get("model_id") or "").strip(), "missing model_id")
        self.assertTrue(str(o.get("method") or "").strip(), "missing method")
        self.assertTrue(str(o.get("category") or "").strip(), "missing category")
        self.assertIsInstance(o.get("evidence"), dict)
        self.assertTrue(str(o.get("cue_id") or "").strip(), "missing cue_id")
        self.assertIn(o.get("priority"), ("normal", "high"))
        cue = str(o.get("cue") or "")
        blob = f"{label} {cue} {json.dumps(o.get('evidence', {}), sort_keys=True)}"
        m = FORBIDDEN_TEXT.search(blob)
        self.assertIsNone(m, f"forbidden term in observation: {m.group(0) if m else ''}")

    def test_language_audit_emitted_observations(self):
        # Task 1: observer labels/cue strings/evidence must not contain forbidden verdict terms.
        for cls in ALL_OBSERVERS:
            obs = cls().observe(REPRESENTATIVE).to_dicts()
            for o in obs:
                self._assert_contract(o)
        for runner in (default_runner(), full_runner()):
            for name in ("owner_clean_interview.json", "owner_conflict_interview.json", "owner_hedging_interview.json", "sample_transcript.json"):
                obs = (runner.build_package(_load_fixture(name)).get("observations") or [])
                for o in obs:
                    self._assert_contract(o)

    def test_confidence_bounds_all_emitted(self):
        # Task 2: scores heuristic, clamped to [0,1].
        for cls in ALL_OBSERVERS:
            for o in cls().observe(REPRESENTATIVE).to_dicts():
                s = (o.get("confidence") or {}).get("score")
                self.assertIsInstance(s, (int, float))
                self.assertGreaterEqual(s, 0.0)
                self.assertLessEqual(s, 1.0)

    def test_insufficient_data_no_cues_no_errors(self):
        # Task 3: thin/empty/noise inputs yield no observations (not errors).
        cases = [
            [],
            [{}],
            [{"role": "subject", "text": ""}],
            [{"role": "subject", "text": "   \n\t  "}],
            [{"role": "subject", "text": "a"}],
            [{"role": "subject", "text": "ok"}],
            [{"role": "subject", "text": "uh"}],
            [None, {"role": "interviewer", "text": "question"}, {"text": ""}],
            [{"role": "subject"}],
        ]
        for cls in ALL_OBSERVERS:
            for t in cases:
                try:
                    obs = cls().observe(t).to_dicts()  # type: ignore[arg-type]
                except Exception as e:
                    self.fail(f"{cls.__name__} raised on insufficient data {t!r}: {e}")
                self.assertIsInstance(obs, list)
                # Single-token/noise may occasionally emit nothing; never emit forbidden/invalid.
                for o in obs:
                    self._assert_contract(o)
        for runner in (default_runner(), full_runner()):
            for t in cases:
                pkg = runner.build_package(t)  # type: ignore[arg-type]
                for o in (pkg.get("observations") or []):
                    self._assert_contract(o)

    def test_neutral_contract_fields_present(self):
        # Task 4: every observation has neutral label, score, non-empty model_id, method, category, evidence.
        for cls in ALL_OBSERVERS:
            for o in cls().observe(REPRESENTATIVE).to_dicts():
                self._assert_contract(o)

    def test_reproducibility_deterministic(self):
        # Task 5: same input => same observations/cue_ids.
        for runner in (default_runner(), full_runner()):
            t = _load_fixture("owner_conflict_interview.json")
            a = runner.build_package(t).get("observations") or []
            b = runner.build_package(t).get("observations") or []
            self.assertEqual(
                [(o.get("cue_id"), o.get("label"), o.get("method"), o.get("turn_index"), (o.get("confidence") or {}).get("score")) for o in a],
                [(o.get("cue_id"), o.get("label"), o.get("method"), o.get("turn_index"), (o.get("confidence") or {}).get("score")) for o in b],
            )


if __name__ == "__main__":
    unittest.main()
