"""Phase 2 (kilo): audio-only real-time indicator path (observers consume derived features/metadata).

Real code, gated by default (not in default_runner). No raw audio processing.
"""
import unittest

from cueliez.gates import SessionGateState, record_consent
from cueliez.observations import default_runner, full_runner
from cueliez.observations.behavioral import ResponseLatencyObserver, SpeechRateShiftObserver
from cueliez.observations.modality_gates import check_modality_allowed
from cueliez.observations.prosody import PausePatternObserver, ProsodicVariabilityObserver


class TestAudioRealtimePathPhase2Kilo(unittest.TestCase):
    def test_gated_by_default(self):
        ids = {getattr(o, "method_id", "") for o in default_runner().observers}
        # Acoustic feature/prosody observers gated (full_runner + metadata/consent flow).
        self.assertNotIn("cueliez.observations.prosody.pause_pattern/v1", ids)
        self.assertNotIn("cueliez.observations.prosody.variability_shift/v1", ids)
        # Latency/speech-rate are behavioral metadata observers in the default text path.
        self.assertIn("cueliez.observations.behavioral.response_latency/v1", ids)
        self.assertIn("cueliez.observations.behavioral.speech_rate_shift/v1", ids)

    def test_modality_gate_required_before_enabling_audio_features(self):
        s = SessionGateState(mode="interrogation")
        with self.assertRaises(Exception):
            check_modality_allowed(s, "audio_features")
        from cueliez.gates import record_modality_consent
        record_modality_consent(s, "audio_features", attested_by="o", jurisdiction="jx", jurisdiction_approved=True)
        check_modality_allowed(s, "audio_features")

    def test_prosody_pause_observer_real_path(self):
        t = [
            {"role": "subject", "text": "a", "pause_total_ms": 200},
            {"role": "subject", "text": "b", "pause_total_ms": 220},
            {"role": "subject", "text": "c", "pause_total_ms": 210},
            {"role": "subject", "text": "d", "pause_total_ms": 2500},
        ]
        obs = PausePatternObserver().observe(t).to_dicts()
        self.assertTrue(obs)
        self.assertEqual(obs[0]["category"], "prosody")

    def test_prosody_variability_real_path(self):
        t = [
            {"role": "subject", "text": "a", "pitch_variance": 10},
            {"role": "subject", "text": "b", "pitch_variance": 11},
            {"role": "subject", "text": "c", "pitch_variance": 10},
            {"role": "subject", "text": "d", "pitch_variance": 80},
        ]
        obs = ProsodicVariabilityObserver().observe(t).to_dicts()
        self.assertTrue(obs)

    def test_latency_and_speech_rate_real_path(self):
        t = [
            {"role": "subject", "text": "one two three four five", "response_latency_ms": 800, "duration_ms": 3000},
            {"role": "subject", "text": "one two three four five", "response_latency_ms": 900, "duration_ms": 3200},
            {"role": "subject", "text": "one two three four five", "response_latency_ms": 850, "duration_ms": 3100},
            {"role": "subject", "text": "one two three four five", "response_latency_ms": 9000, "duration_ms": 900},
        ]
        self.assertTrue(ResponseLatencyObserver().observe(t).to_dicts())
        # speech rate may or may not fire depending on threshold; ensure no error and valid structure
        sr = SpeechRateShiftObserver().observe(t).to_dicts()
        for o in sr:
            self.assertEqual(o["category"], "behavioral")

    def test_full_runner_consumes_audio_metadata_when_provided(self):
        t = [
            {"role": "subject", "text": "ok fine", "pause_total_ms": 200},
            {"role": "subject", "text": "ok fine", "pause_total_ms": 210},
            {"role": "subject", "text": "ok fine", "pause_total_ms": 220},
            {"role": "subject", "text": "ok fine", "pause_total_ms": 3000},
        ]
        obs = full_runner().build_package(t).get("observations") or []
        self.assertTrue(any(o.get("method") == "cueliez.observations.prosody.pause_pattern/v1" for o in obs), obs)


if __name__ == "__main__":
    unittest.main()
