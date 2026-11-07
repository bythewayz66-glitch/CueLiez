import unittest

from cueliez.gates import seal_observation_package
from cueliez.observations.multimodal import CrossModalConvergenceObserver, add_convergence_observations
from cueliez.observations.physiological import ElectrodermalShiftObserver, HeartRateShiftObserver, HrvShiftObserver
from cueliez.observations.prosody import PausePatternObserver, ProsodicVariabilityObserver, VoiceStressFeatureShiftObserver
from cueliez.observations.visual import BlinkRateObserver, GazePatternObserver, MotorActivityObserver


class TestProsody(unittest.TestCase):
    def test_variability_shift(self):
        base = {"role": "subject", "text": "answer", "prosody": {"pitch_variance": 10.0}}
        t = [dict(base) for _ in range(3)] + [{"role": "subject", "text": "answer", "prosody": {"pitch_variance": 80.0}}]
        obs = ProsodicVariabilityObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "prosodic_variability_shift_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_pause_pattern(self):
        t = [{"role": "subject", "text": "a", "pause_total_ms": 200}] * 3 + [{"role": "subject", "text": "a", "pause_total_ms": 5000}]
        obs = PausePatternObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "pause_duration_elevated_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_acoustic_feature_shift(self):
        t = [{"role": "subject", "text": "a", "jitter": 0.01}] * 3 + [{"role": "subject", "text": "a", "jitter": 0.2}]
        obs = VoiceStressFeatureShiftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "acoustic_feature_shift_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_insufficient_data(self):
        for cls in (ProsodicVariabilityObserver, PausePatternObserver, VoiceStressFeatureShiftObserver):
            res = cls().observe([{"role": "subject", "text": "hi"}])
            self.assertEqual(res.observations, [])
            self.assertTrue(res.notes)


class TestVisual(unittest.TestCase):
    def test_gaze_shift(self):
        t = [{"role": "subject", "text": "a", "gaze_aversion_ratio": 0.1}] * 3 + [{"role": "subject", "text": "a", "gaze_aversion_ratio": 0.95}]
        obs = GazePatternObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "gaze_pattern_shift_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_blink_shift(self):
        t = [{"role": "subject", "text": "a", "blink_rate_per_min": 15}] * 3 + [{"role": "subject", "text": "a", "blink_rate_per_min": 60}]
        obs = BlinkRateObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "blink_rate_shift_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_motor_activity(self):
        t = [{"role": "subject", "text": "a", "gesture_count": 1, "head_movement_events": 0}] * 3 + [
            {"role": "subject", "text": "a", "gesture_count": 20, "head_movement_events": 10}]
        obs = MotorActivityObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "motor_activity_shift_observed" for o in obs))
        seal_observation_package({"observations": obs})


class TestPhysiological(unittest.TestCase):
    def test_heart_rate_shift(self):
        t = [{"role": "subject", "text": "a", "heart_rate_bpm": 72}] * 3 + [{"role": "subject", "text": "a", "heart_rate_bpm": 130}]
        obs = HeartRateShiftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "heart_rate_shift_observed" for o in obs))
        # language check: cues must not claim deception
        for o in obs:
            self.assertNotIn("lying", o.get("cue", "").lower())
            self.assertNotIn("deception", o.get("cue", "").lower())
        seal_observation_package({"observations": obs})

    def test_hrv_shift(self):
        t = [{"role": "subject", "text": "a", "hrv_ms": 50}] * 3 + [{"role": "subject", "text": "a", "hrv_ms": 10}]
        obs = HrvShiftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "hrv_shift_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_electrodermal(self):
        t = [{"role": "subject", "text": "a", "eda": 1.0}] * 3 + [{"role": "subject", "text": "a", "eda": 12.0}]
        obs = ElectrodermalShiftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "electrodermal_activity_shift_observed" for o in obs))
        seal_observation_package({"observations": obs})


class TestMultimodal(unittest.TestCase):
    def test_convergence(self):
        obs = [
            {"label": "a", "confidence": {"score": 0.5, "model_id": "m"}, "category": "linguistic", "turn_index": 3},
            {"label": "b", "confidence": {"score": 0.5, "model_id": "m"}, "category": "prosody", "turn_index": 3},
        ]
        res = CrossModalConvergenceObserver().observe_observations(obs)
        dicts = res.to_dicts()
        self.assertTrue(any(o["label"] == "multi_indicator_convergence_observed" for o in dicts))
        self.assertEqual(dicts[0]["turn_index"], 3)
        seal_observation_package({"observations": dicts})

    def test_no_convergence_when_different_turns(self):
        obs = [
            {"label": "a", "confidence": {"score": 0.5, "model_id": "m"}, "category": "linguistic", "turn_index": 1},
            {"label": "b", "confidence": {"score": 0.5, "model_id": "m"}, "category": "prosody", "turn_index": 2},
        ]
        self.assertEqual(CrossModalConvergenceObserver().observe_observations(obs).to_dicts(), [])

    def test_add_convergence(self):
        obs = [{"label": "a", "confidence": {"score": 0.5, "model_id": "m"}, "category": "linguistic", "turn_index": 1},
               {"label": "b", "confidence": {"score": 0.5, "model_id": "m"}, "category": "visual", "turn_index": 1}]
        out = add_convergence_observations(obs)
        self.assertGreater(len(out), 2)
        seal_observation_package({"observations": out})

    def test_observe_transcript_noop(self):
        res = CrossModalConvergenceObserver().observe([])
        self.assertEqual(res.observations, [])
        self.assertIn("requires_observation_inputs", res.notes)


if __name__ == "__main__":
    unittest.main()
