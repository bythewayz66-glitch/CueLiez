"""Phase 7 (kilo): consent-governed audio-feature observation hook (no raw audio)."""
import unittest

from cueliez.gates import GateError, SessionGateState, record_modality_consent
from cueliez.observations.audio_path import observe_audio_features


class TestAudioHookPhase7Kilo(unittest.TestCase):
    def test_requires_modality_consent(self):
        s = SessionGateState(mode="interrogation")
        with self.assertRaises(GateError):
            observe_audio_features([], state=s)
        record_modality_consent(s, "audio_features", attested_by="o", jurisdiction="jx", jurisdiction_approved=True)
        self.assertEqual(observe_audio_features([], state=s), [])

    def test_runs_on_derived_metadata(self):
        s = SessionGateState(mode="generic")
        record_modality_consent(s, "audio_features", attested_by="o", jurisdiction="jx", jurisdiction_approved=True)
        t = [
            {"role": "subject", "text": "a", "pause_total_ms": 200, "response_latency_ms": 500},
            {"role": "subject", "text": "b", "pause_total_ms": 210, "response_latency_ms": 520},
            {"role": "subject", "text": "c", "pause_total_ms": 220, "response_latency_ms": 510},
            {"role": "subject", "text": "d", "pause_total_ms": 3000, "response_latency_ms": 6000},
        ]
        obs = observe_audio_features(t, state=s)
        self.assertIsInstance(obs, list)
        self.assertTrue(any(o.get("method", "").startswith("cueliez.observations.prosody") or "response_latency" in o.get("method", "") for o in obs))


if __name__ == "__main__":
    unittest.main()
