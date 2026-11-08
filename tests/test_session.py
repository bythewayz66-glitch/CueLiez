import unittest

from cueliez.gates import GateError, SessionGateState, record_consent, seal_observation_package
from cueliez.session import assert_can_observe, extract_high_priority_cue_ids, seal, start_session


def _valid_obs():
    return {"label": "x", "confidence": {"score": 0.5, "model_id": "m/v1"}, "method": "m/v1", "category": "behavioral", "evidence": {}}


class TestSessionLifecycle(unittest.TestCase):
    def test_start_session_fails_without_consent(self):
        s = SessionGateState(mode="interrogation", training_acknowledged=True, training_version="v1")
        with self.assertRaises(GateError) as ctx:
            start_session(s)
        self.assertEqual(ctx.exception.code, "consent_required")

    def test_start_session_fails_without_training(self):
        s = SessionGateState(mode="interrogation")
        record_consent(s, attested_by="off")
        with self.assertRaises(GateError) as ctx:
            start_session(s)
        self.assertEqual(ctx.exception.code, "training_required")

    def test_start_session_succeeds_when_ready(self):
        s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        self.assertIs(start_session(s), s)

    def test_start_session_generic_succeeds(self):
        s = SessionGateState(mode="generic")
        self.assertIs(start_session(s), s)

    def test_assert_can_observe_fails_closed(self):
        s = SessionGateState(mode="clinical", training_acknowledged=True, training_version="v1")
        with self.assertRaises(GateError):
            assert_can_observe(s)
        record_consent(s, attested_by="clin")
        assert_can_observe(s)

    def test_seal_wrapper_fail_closed(self):
        s = SessionGateState(mode="government", intended_uses=["interview support"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        with self.assertRaises(GateError) as ctx:
            seal({"observations": [_valid_obs()]}, s, high_priority_cue_ids=["hp1"])
        self.assertEqual(ctx.exception.code, "dual_control_incomplete")
        from cueliez.gates import record_dual_acknowledge
        record_dual_acknowledge(s, "hp1", "a", "b")
        out = seal({"observations": [_valid_obs()]}, s, high_priority_cue_ids=["hp1"])
        self.assertTrue(out["sealed"])


class TestHighPriorityCueExtraction(unittest.TestCase):
    def test_extracts_from_cues(self):
        pkg = {"cues": [{"cue_id": "c1", "priority": "high"}, {"cue_id": "c2", "priority": "low"}, {"cue_id": "c3", "priority": "critical"}]}
        self.assertEqual(extract_high_priority_cue_ids(pkg), ["c1", "c3"])

    def test_extracts_from_observations(self):
        pkg = {"observations": [{"id": "o1", "priority": "HIGH", "label": "x", "confidence": {"score": 0.5, "model_id": "m"}, "method": "m", "category": "c"}]}
        self.assertEqual(extract_high_priority_cue_ids(pkg), ["o1"])

    def test_dedupes_and_ignores_missing_ids(self):
        pkg = {"cues": [{"cue_id": "c1", "priority": "high"}, {"priority": "high"}, {"cue_id": "c1", "priority": "high"}]}
        self.assertEqual(extract_high_priority_cue_ids(pkg), ["c1"])

    def test_government_seal_fails_on_extracted_high_priority_without_dual_control(self):
        s = SessionGateState(mode="government", intended_uses=["interview support"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        pkg = {"observations": [_valid_obs()], "cues": [{"cue_id": "cue-t1-x-0", "priority": "high"}]}
        with self.assertRaises(GateError) as ctx:
            seal_observation_package(pkg, s)  # auto-extract
        self.assertEqual(ctx.exception.code, "dual_control_incomplete")

    def test_explicit_empty_high_priority_overrides_extraction(self):
        s = SessionGateState(mode="government", intended_uses=["interview support"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        pkg = {"observations": [_valid_obs()], "cues": [{"cue_id": "cue-t1-x-0", "priority": "high"}]}
        out = seal_observation_package(pkg, s, high_priority_cue_ids=[])
        self.assertTrue(out["sealed"])


class TestPostSealImmutability(unittest.TestCase):
    def test_attach_notes_refused_after_seal(self):
        from cueliez.delivery.notes import attach_officer_cue_notes
        s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        sealed = seal_observation_package({"observations": [_valid_obs()]}, s)
        with self.assertRaises(ValueError) as ctx:
            attach_officer_cue_notes(sealed, [{"cue_id": "c1", "note": "late"}])
        self.assertIn("before seal", str(ctx.exception))

    def test_is_sealed_and_assert_not_sealed(self):
        from cueliez.gates import assert_not_sealed, is_sealed
        self.assertFalse(is_sealed({"observations": []}))
        s = SessionGateState(mode="generic")
        sealed = seal_observation_package({"observations": [_valid_obs()]}, s)
        self.assertTrue(is_sealed(sealed))
        with self.assertRaises(GateError):
            assert_not_sealed(sealed, action="edit")


if __name__ == "__main__":
    unittest.main()
