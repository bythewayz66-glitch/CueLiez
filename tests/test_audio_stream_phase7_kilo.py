import unittest

from cueliez.gates import SessionGateState, record_modality_consent
from cueliez.observations.audio_stream import AudioStreamHook, stream_audio_features


class TestAudioStream(unittest.TestCase):
    def _state(self):
        s = SessionGateState(mode="generic")
        record_modality_consent(s, "audio_features", attested_by="officer/a", jurisdiction="J", jurisdiction_approved=True)
        return s

    def test_requires_consent(self):
        s = SessionGateState(mode="generic")
        hook = AudioStreamHook(state=s, require_consent_check=True)
        with self.assertRaises(Exception):
            hook.push_turn({"role": "subject", "text": "hi", "response_latency_ms": 3000})

    def test_stream_emits(self):
        s = self._state()
        turns = [
            {"role": "subject", "text": "a", "response_latency_ms": 1000},
            {"role": "subject", "text": "b", "response_latency_ms": 5000},
            {"role": "subject", "text": "c", "response_latency_ms": 5200},
        ]
        out = stream_audio_features(turns, state=s)
        self.assertIsInstance(out, list)

    def test_incremental(self):
        s = self._state()
        hook = AudioStreamHook(state=s, require_consent_check=True)
        t1 = hook.push_turn({"role": "subject", "text": "a", "response_latency_ms": 1000})
        t2 = hook.push_turn({"role": "subject", "text": "b", "response_latency_ms": 5000})
        self.assertIsInstance(t1, list)
        self.assertIsInstance(t2, list)


if __name__ == "__main__":
    unittest.main()