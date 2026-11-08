"""Phase 2 (kilo): consent + jurisdiction checks before gated modality enablement."""
import unittest

from cueliez.gates import GateError, SessionGateState, record_consent
from cueliez.observations.modality_gates import check_modality_allowed, modality_observers_allowed


class TestModalityGatesPhase2Kilo(unittest.TestCase):
    def test_text_always_allowed(self):
        check_modality_allowed(SessionGateState(mode="interrogation"), "text")

    def test_sensitive_requires_consent_in_governed_mode(self):
        s = SessionGateState(mode="interrogation")
        with self.assertRaises(GateError) as ctx:
            check_modality_allowed(s, "audio_features")
        self.assertEqual(ctx.exception.code, "modality_consent_required")
        record_consent(s, attested_by="off1", jurisdiction="test-jx")
        check_modality_allowed(s, "audio_features")
        check_modality_allowed(s, "visual_features")
        check_modality_allowed(s, "physiological_features")

    def test_sensitive_requires_jurisdiction(self):
        s = SessionGateState(mode="generic", consent=True, consent_recorded_at=1.0, consent_attested_by="x")
        with self.assertRaises(GateError) as ctx:
            check_modality_allowed(s, "audio_features", require_jurisdiction=True)
        self.assertEqual(ctx.exception.code, "modality_jurisdiction_required")
        check_modality_allowed(s, "audio_features", require_jurisdiction=False)
        s.jurisdiction = "JX"
        check_modality_allowed(s, "audio_features")

    def test_dict_state(self):
        with self.assertRaises(GateError):
            check_modality_allowed({"mode": "clinical", "consent": False}, "audio_features")
        check_modality_allowed(
            {"mode": "clinical", "consent": True, "consent_recorded_at": 1.0, "consent_attested_by": "c", "jurisdiction": "J"},
            "audio_features",
        )

    def test_modality_observers_allowed_helper(self):
        s = SessionGateState(mode="interrogation")
        self.assertFalse(modality_observers_allowed(s, "audio_features"))
        record_consent(s, attested_by="o", jurisdiction="j")
        self.assertTrue(modality_observers_allowed(s, "audio_features"))


if __name__ == "__main__":
    unittest.main()
