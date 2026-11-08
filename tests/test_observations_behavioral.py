import unittest

from cueliez.gates import seal_observation_package
from cueliez.observations.behavioral import (
    AnswerLengthVarianceObserver,
    EvasionMarkerObserver,
    FilledPauseMarkerObserver,
    InterruptionOverlapObserver,
    ResponseLatencyObserver,
    SpeechRateShiftObserver,
)


class TestBehavioral(unittest.TestCase):
    def test_latency_anomaly(self):
        t = [
            {"role": "subject", "text": "ok", "response_latency_ms": 400},
            {"role": "subject", "text": "ok", "response_latency_ms": 450},
            {"role": "subject", "text": "ok", "response_latency_ms": 500},
            {"role": "subject", "text": "ok", "response_latency_ms": 6000},
        ]
        obs = ResponseLatencyObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "response_latency_anomaly_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_latency_insufficient(self):
        res = ResponseLatencyObserver().observe([{"role": "subject", "text": "hi"}])
        self.assertIn("insufficient_latency_data", res.notes)
        seal_observation_package({"observations": res.to_dicts()})

    def test_brief_response(self):
        long = {"role": "subject", "text": "I was at the store with my friend for about twenty minutes talking about many different things in detail."}
        t = [long, long, long, long, {"role": "subject", "text": "No."}]
        obs = AnswerLengthVarianceObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "notably_brief_response_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_evasion(self):
        t = [{"role": "subject", "text": "Why would you ask that? I already told you, let's move on."}]
        obs = EvasionMarkerObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "question_deflection_markers_present" for o in obs))
        seal_observation_package({"observations": obs})

    def test_speech_rate(self):
        t = [
            {"role": "subject", "text": "one two three four five six seven eight nine ten", "duration_ms": 4000},
            {"role": "subject", "text": "one two three four five six seven eight nine ten", "duration_ms": 4200},
            {"role": "subject", "text": "one two three four five six seven eight nine ten", "duration_ms": 3900},
            {"role": "subject", "text": "one two three four five six seven eight nine ten", "duration_ms": 1600},
        ]
        obs = SpeechRateShiftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "speech_rate_shift_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_filled_pauses(self):
        t = [{"role": "subject", "text": "um um uh I went there er um and uh yes", "filler_count": 6}]
        obs = FilledPauseMarkerObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "filled_pause_markers_elevated" for o in obs))
        seal_observation_package({"observations": obs})

    def test_interruption(self):
        t = [{"role": "subject", "text": "I was saying", "interrupted": True, "overlap_ms": 400}]
        obs = InterruptionOverlapObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "turn_overlap_or_interruption_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_empty_safe(self):
        for cls in (ResponseLatencyObserver, AnswerLengthVarianceObserver, EvasionMarkerObserver,
                    SpeechRateShiftObserver, FilledPauseMarkerObserver, InterruptionOverlapObserver):
            seal_observation_package({"observations": cls().observe([]).to_dicts()})

    def test_sprint2_single_turn_noise_precision(self):
        # Insufficient or thin behavioral evidence should emit no cues.
        self.assertEqual(ResponseLatencyObserver().observe(
            [{"role": "subject", "text": "ok", "response_latency_ms": 5000}]
        ).to_dicts(), [])
        self.assertEqual(ResponseLatencyObserver().observe([
            {"role": "subject", "text": "ok", "response_latency_ms": 500},
            {"role": "subject", "text": "ok", "response_latency_ms": 520},
            {"role": "subject", "text": "ok", "response_latency_ms": 480},
            {"role": "subject", "text": "ok", "response_latency_ms": 510},
        ]).to_dicts(), [])
        self.assertEqual(AnswerLengthVarianceObserver().observe(
            [{"role": "subject", "text": "No."}]
        ).to_dicts(), [])
        self.assertEqual(EvasionMarkerObserver().observe(
            [{"role": "subject", "text": "I do not know what happened there."}]
        ).to_dicts(), [])


if __name__ == "__main__":
    unittest.main()
