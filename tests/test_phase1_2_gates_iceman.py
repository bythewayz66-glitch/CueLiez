"""Phase 1+2 implementation (iceman, 0835): modality consent+jurisdiction, session hardening, immutability."""
import unittest

from cueliez.gates import (
    GATED_INPUT_MODALITIES,
    GateError,
    SessionGateState,
    assert_not_sealed,
    is_sealed,
    record_consent,
    record_dual_acknowledge,
    record_modality_consent,
    require_gated_modality,
    seal_observation_package,
)
from cueliez.session import assert_can_observe, seal, start_session


def _valid_obs(label="indicator_present"):
    return {"label": label, "confidence": {"score": 0.5, "model_id": "m/v1"}, "method": "m/v1", "category": "behavioral", "evidence": {}}


def _ready_interrogation():
    s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
    record_consent(s, attested_by="officer/a", jurisdiction="TestJurisdiction")
    s.training_acknowledged = True
    s.training_version = "v1"
    return s


class TestGatedModalityConsentJurisdiction(unittest.TestCase):
    def test_gated_modalities_defined(self):
        self.assertEqual(GATED_INPUT_MODALITIES, {"audio_features", "camera", "wearable"})

    def test_require_gated_modality_fails_without_explicit_consent(self):
        s = _ready_interrogation()
        with self.assertRaises(GateError) as ctx:
            require_gated_modality(s, "audio_features")
        self.assertEqual(ctx.exception.code, "modality_consent_required")

    def test_require_gated_modality_fails_without_jurisdiction(self):
        s = SessionGateState(mode="generic")
        record_modality_consent(s, "camera", attested_by="att", jurisdiction="", jurisdiction_approved=True)
        s.jurisdiction = None
        s.jurisdiction_approved = False
        s.modality_consents["camera"]["jurisdiction"] = None
        s.modality_consents["camera"]["jurisdiction_approved"] = False
        with self.assertRaises(GateError) as ctx:
            require_gated_modality(s, "camera")
        self.assertEqual(ctx.exception.code, "jurisdiction_required")

    def test_require_gated_modality_fails_without_jurisdiction_approval(self):
        s = SessionGateState(mode="generic")
        record_modality_consent(s, "wearable", attested_by="att", jurisdiction="J1", jurisdiction_approved=False)
        s.jurisdiction_approved = False
        with self.assertRaises(GateError) as ctx:
            require_gated_modality(s, "wearable")
        self.assertEqual(ctx.exception.code, "jurisdiction_approval_required")

    def test_require_gated_modality_succeeds_with_consent_and_jurisdiction(self):
        s = _ready_interrogation()
        record_modality_consent(s, "audio_features", attested_by="officer/a", jurisdiction="TestJurisdiction")
        require_gated_modality(s, "audio_features")
        require_gated_modality(s, "audio-features")  # normalization

    def test_record_modality_consent_requires_attester(self):
        s = SessionGateState(mode="generic")
        with self.assertRaises(GateError) as ctx:
            record_modality_consent(s, "camera", attested_by="")
        self.assertEqual(ctx.exception.code, "consent_attester_required")

    def test_unsupported_gated_modality(self):
        s = SessionGateState(mode="generic")
        with self.assertRaises(GateError) as ctx:
            record_modality_consent(s, "telepathy", attested_by="att")
        self.assertEqual(ctx.exception.code, "unsupported_gated_modality")

    def test_assert_can_observe_checks_modalities(self):
        s = _ready_interrogation()
        assert_can_observe(s)  # no modalities
        with self.assertRaises(GateError) as ctx:
            assert_can_observe(s, modalities=["camera"])
        self.assertEqual(ctx.exception.code, "modality_consent_required")
        record_modality_consent(s, "camera", attested_by="officer/a", jurisdiction="TestJurisdiction")
        assert_can_observe(s, modalities=["camera"])

    def test_assert_can_observe_repeatable_with_modalities(self):
        s = _ready_interrogation()
        record_modality_consent(s, "audio_features", attested_by="officer/a", jurisdiction="TestJurisdiction")
        for _ in range(4):
            assert_can_observe(s, modalities=["audio_features"])
        start_session(s)


class TestDualControlGovernment(unittest.TestCase):
    def test_government_seal_requires_dual_control_for_high_priority(self):
        s = SessionGateState(mode="government", intended_uses=["interview support"])
        record_consent(s, attested_by="att")
        s.training_acknowledged = True
        s.training_version = "v1"
        pkg = {"observations": [_valid_obs()], "cues": [{"cue_id": "hp1", "priority": "high"}]}
        with self.assertRaises(GateError) as ctx:
            seal_observation_package(pkg, s)
        self.assertEqual(ctx.exception.code, "dual_control_incomplete")
        record_dual_acknowledge(s, "hp1", "o1", "o2")
        out = seal_observation_package(pkg, s)
        self.assertTrue(out["sealed"])
        self.assertTrue(out["gate_state"]["requirements"]["dual_control_required"])


class TestPostSealImmutability(unittest.TestCase):
    def test_reseal_refused(self):
        out = seal_observation_package({"observations": [_valid_obs()]}, SessionGateState(mode="generic"))
        with self.assertRaises(GateError) as ctx:
            seal_observation_package(out)
        self.assertEqual(ctx.exception.code, "package_sealed")

    def test_assert_not_sealed(self):
        out = seal_observation_package({"observations": [_valid_obs()]}, SessionGateState(mode="generic"))
        self.assertTrue(is_sealed(out))
        with self.assertRaises(GateError):
            assert_not_sealed(out)

    def test_gate_state_captures_modality_consent(self):
        s = _ready_interrogation()
        record_modality_consent(s, "camera", attested_by="officer/a", jurisdiction="TestJurisdiction")
        out = seal_observation_package({"observations": [_valid_obs()]}, s)
        gs = out.get("gate_state") or {}
        self.assertIn("modality_consents", gs)
        self.assertIn("camera", gs["modality_consents"])
        self.assertTrue(gs["modality_consents"]["camera"]["consented"])
