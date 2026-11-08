import unittest

from cueliez.observations import default_runner, full_runner
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

ALL_TEXT_BEHAVIORAL = [
    HedgingObserver, PronounDistancingObserver, NegationDensityObserver, DetailVaguenessObserver,
    CertaintySwingObserver, MinimizationObserver, PassiveVoiceProxyObserver, OverjustificationObserver,
    MemoryQualifierObserver, ClaimConflictObserver, TimelineInconsistencyObserver, DetailDriftObserver,
    LocationReferenceDivergenceObserver, SelfReferenceShiftObserver, ResponseLatencyObserver,
    AnswerLengthVarianceObserver, EvasionMarkerObserver, SpeechRateShiftObserver,
    FilledPauseMarkerObserver, InterruptionOverlapObserver,
]


class TestInsufficientData(unittest.TestCase):
    def test_empty_transcript_no_observations(self):
        for cls in ALL_TEXT_BEHAVIORAL:
            self.assertEqual(cls().observe([]).to_dicts(), [], cls.__name__)
        self.assertEqual(default_runner().build_package([])["observations"], [])

    def test_single_token_no_low_confidence_noise(self):
        t = [{"role": "subject", "text": "ok"}]
        for cls in ALL_TEXT_BEHAVIORAL:
            obs = cls().observe(t).to_dicts()
            self.assertEqual(obs, [], f"{cls.__name__} emitted on single token: {obs}")

    def test_null_and_invalid_turns_no_crash_no_noise(self):
        t = [None, {"role": "subject", "text": "ok"}, "bad", 123, {"role": "interviewer", "text": "hi"}, {"text": "   "}]
        for cls in ALL_TEXT_BEHAVIORAL:
            obs = cls().observe(t).to_dicts()  # type: ignore[arg-type]
            # Must not crash; single-token subject content should not produce noisy cues.
            self.assertIsInstance(obs, list, cls.__name__)
        pkg = default_runner().build_package(t)  # type: ignore[arg-type]
        self.assertIsInstance(pkg["observations"], list)


if __name__ == "__main__":
    unittest.main()
