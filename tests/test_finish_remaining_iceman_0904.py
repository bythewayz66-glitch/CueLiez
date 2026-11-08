"""0904 finish remaining (iceman): RMS attachment readiness, pilot boundaries, gate readiness."""
import unittest

from cueliez import (
    GateError,
    SessionGateState,
    build_ingested_package,
    custody_receipt,
    record_consent,
    require_gated_modality,
    seal_observation_package,
    validate_sealed_package_ingest,
)
from cueliez.gates import record_dual_acknowledge


class TestRmsAttachmentReadiness(unittest.TestCase):
    def test_sealed_original_artifact_validates_for_ingest(self):
        pkg = build_ingested_package({"turns": [{"role": "i", "text": "test"}]})
        sealed = seal_observation_package(pkg, SessionGateState(mode="generic"))
        receipt = validate_sealed_package_ingest(sealed)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["epistemic_status"], "observed_indicator")
        cr = custody_receipt(sealed)
        self.assertEqual(cr["package_hash"], sealed["package_hash"])
        self.assertIn("disclaimer_version", cr)


class TestPilotBoundaries(unittest.TestCase):
    def test_government_dual_control_enforced(self):
        s = SessionGateState(mode="government", intended_uses=["interview support"])
        record_consent(s, attested_by="a")
        s.training_acknowledged = True
        s.training_version = "v1"
        pkg = {"observations": [{"label": "x", "confidence": {"score": 0.5, "model_id": "m"}, "method": "m", "category": "behavioral", "evidence": {}}],
               "cues": [{"cue_id": "h1", "priority": "high"}]}
        with self.assertRaises(GateError):
            seal_observation_package(pkg, s)
        record_dual_acknowledge(s, "h1", "o1", "o2")
        self.assertTrue(seal_observation_package(pkg, s)["sealed"])

    def test_gated_modalities_fail_closed_when_enabled_by_policy_path(self):
        # Gates remain fail-closed regardless of future default-enable policy.
        s = SessionGateState(mode="generic")
        with self.assertRaises(GateError):
            require_gated_modality(s, "audio_features")
