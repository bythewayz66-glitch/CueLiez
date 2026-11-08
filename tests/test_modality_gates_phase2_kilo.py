"""Phase 2 (kilo): consent + jurisdiction checks for gated modalities (aligned to canonical gates)."""
import unittest

from cueliez.gates import GateError, SessionGateState, record_consent, record_modality_consent
from cueliez.observations.modality_gates import check_modality_allowed, modality_observers_allowed


class TestModalityGatesPhase2Kilo(unittest.TestCase):
    def test_text_always_allowed(self):
        check_modality_allowed(SessionGateState(mode="interrogation"), "text")

    def test_sensitive_requires_explicit_modality_consent(self):
        s = SessionGateState(mode="interrogation")
        record_consent(s, attested_by="off1", jurisdiction="test-jx")
        with self.assertRaises(GateError) as ctx:
            check_modality_allowed(s, "audio_features")
        self.assertEqual(ctx.exception.code, "modality_consent_required")
        record_modality_consent(s, "audio_features", attested_by="off1", jurisdiction="test-jx", jurisdiction_approved=True)
        check_modality_allowed(s, "audio_features")
        # aliases map to canonical camera/wearable
        record_modality_consent(s, "camera", attested_by="off1", jurisdiction="test-jx", jurisdiction_approved=True)
        check_modality_allowed(s, "visual_features")
        record_modality_consent(s, "wearable", attested_by="off1", jurisdiction="test-jx", jurisdiction_approved=True)
        check_modality_allowed(s, "physiological_features")

    def test_canonical_requires_jurisdiction_approval(self):
        s = SessionGateState(mode="generic")
        # In generic mode, still need explicit per-modality record with jurisdiction+approval per canonical gate
        with self.assertRaises(GateError):
            check_modality_allowed(s, "audio_features")
        record_modality_consent(s, "audio_features", attested_by="x", jurisdiction="J", jurisdiction_approved=True)
        check_modality_allowed(s, "audio_features")

    def test_dict_state_with_modality_record(self):
        with self.assertRaises(GateError):
            check_modality_allowed({"mode": "clinical", "consent": False}, "audio_features")
        ok = {
            "mode": "clinical", "consent": True, "consent_recorded_at": 1.0, "consent_attested_by": "c",
            "jurisdiction": "J",
            "modality_consents": {
                "audio_features": {"consented": True, "attested_by": "c", "jurisdiction": "J", "jurisdiction_approved": True}
            },
        }
        check_modality_allowed(ok, "audio_features")

    def test_modality_observers_allowed_helper(self):
        s = SessionGateState(mode="interrogation")
        self.assertFalse(modality_observers_allowed(s, "audio_features"))
        record_modality_consent(s, "audio_features", attested_by="o", jurisdiction="j", jurisdiction_approved=True)
        self.assertTrue(modality_observers_allowed(s, "audio_features"))


if __name__ == "__main__":
    unittest.main()
