import tempfile
import unittest
from pathlib import Path

from cueliez.delivery.notes import attach_officer_cue_notes
from cueliez.gates import (
    GateError,
    SessionGateState,
    assert_not_sealed,
    compute_package_hash,
    custody_receipt,
    extract_high_priority_cue_ids,
    is_sealed,
    record_consent,
    record_dual_acknowledge,
    seal_observation_package,
    sign_package,
    verify_package_hash,
)
from cueliez.memory import ContaminationError, MemoryEngine, SealError
from cueliez.session import assert_can_observe, seal, start_session


def _valid_obs(label="indicator", cue_id=None, priority=None):
    o = {"label": label, "confidence": {"score": 0.5, "model_id": "m/v1"}, "method": "m/v1", "category": "behavioral", "evidence": {}}
    if cue_id is not None:
        o["cue_id"] = cue_id
    if priority is not None:
        o["priority"] = priority
    return o


class TestL3SignatureHook(unittest.TestCase):
    def test_default_signature_optional_no_break(self):
        s = SessionGateState(mode="generic")
        out = seal_observation_package({"observations": [_valid_obs()]}, s)
        self.assertIn("package_signature", out)
        self.assertIsNone(out["package_signature"])
        self.assertTrue(verify_package_hash(out))

    def test_signer_callable(self):
        s = SessionGateState(mode="generic")
        out = seal_observation_package(
            {"observations": [_valid_obs()]}, s,
            signer=lambda package_hash=None, **k: f"sig:{package_hash[:8]}",
        )
        self.assertTrue(str(out["package_signature"]).startswith("sig:"))
        self.assertTrue(verify_package_hash(out))

    def test_sign_package_noop(self):
        p = {"package_hash": "abc"}
        sign_package(p, signer=None)
        self.assertIsNone(p["package_signature"])

    def test_signer_error_does_not_break(self):
        def bad(**k):
            raise RuntimeError("boom")
        s = SessionGateState(mode="generic")
        out = seal_observation_package({"observations": [_valid_obs()]}, s, signer=bad)
        self.assertEqual(out["package_signature"]["type"], "error")


class TestL4GateErrorCodes(unittest.TestCase):
    def test_key_codes_stable(self):
        s = SessionGateState(mode="interrogation", training_acknowledged=True, training_version="v1")
        with self.assertRaises(GateError) as ctx:
            start_session(s)
        self.assertEqual(ctx.exception.code, "consent_required")
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [{"label": "lying", "confidence": {"score": 0.5, "model_id": "m"}, "method": "m", "category": "c"}]})
        self.assertEqual(ctx.exception.code, "verdict_language")
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"annotations": {"diagnosis": "x"}})
        self.assertEqual(ctx.exception.code, "contamination_attempt")
        gov = SessionGateState(mode="government", intended_uses=["interview support"])
        record_consent(gov, attested_by="a")
        gov.training_acknowledged = True
        gov.training_version = "v1"
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [_valid_obs()], "cues": [{"cue_id": "h1", "priority": "high"}]}, gov)
        self.assertEqual(ctx.exception.code, "dual_control_incomplete")


class TestL6Custody(unittest.TestCase):
    def test_verify_package_hash(self):
        s = SessionGateState(mode="generic")
        out = seal_observation_package({"observations": [_valid_obs()]}, s)
        self.assertTrue(verify_package_hash(out))
        out["observations"][0]["label"] = "changed"
        self.assertFalse(verify_package_hash(out))

    def test_custody_receipt(self):
        s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
        record_consent(s, attested_by="off-1")
        s.training_acknowledged = True
        s.training_version = "tv1"
        out = seal_observation_package({"observations": [_valid_obs()]}, s)
        r = custody_receipt(out)
        self.assertEqual(r["mode"], "interrogation")
        self.assertTrue(r["consent_attester_present"])
        self.assertTrue(r["training_acknowledged"])
        self.assertEqual(r["package_hash"], out["package_hash"])
        self.assertEqual(r["epistemic_status"], "observed_indicator")


class TestL7IntegrationPaths(unittest.TestCase):
    def test_interrogation_without_consent_start_fails(self):
        s = SessionGateState(mode="interrogation", training_acknowledged=True, training_version="v1")
        with self.assertRaises(GateError) as ctx:
            start_session(s)
        self.assertEqual(ctx.exception.code, "consent_required")

    def test_interrogation_with_consent_training_observe_seal_ok(self):
        s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        start_session(s)
        assert_can_observe(s)
        out = seal({"observations": [_valid_obs()]}, s)
        self.assertEqual(out["epistemic_status"], "observed_indicator")
        self.assertTrue(out["sealed"])

    def test_government_high_priority_without_dual_control_fails(self):
        s = SessionGateState(mode="government", intended_uses=["interview support"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        pkg = {"observations": [_valid_obs(cue_id="c1", priority="high")]}
        with self.assertRaises(GateError) as ctx:
            seal_observation_package(pkg, s)
        self.assertEqual(ctx.exception.code, "dual_control_incomplete")

    def test_government_with_dual_control_seals_ok(self):
        s = SessionGateState(mode="government", intended_uses=["interview support"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        record_dual_acknowledge(s, "c1", "o1", "o2")
        out = seal_observation_package({"observations": [_valid_obs(cue_id="c1", priority="high")]}, s)
        self.assertTrue(out["sealed"])
        self.assertEqual(len(out["gate_state"]["dual_control_records"]), 1)

    def test_attach_notes_after_seal_fails(self):
        s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        sealed = seal_observation_package({"observations": [_valid_obs()]}, s)
        with self.assertRaises(ValueError):
            attach_officer_cue_notes(sealed, [{"cue_id": "x", "note": "late"}])
        with self.assertRaises(GateError):
            assert_not_sealed(sealed, action="edit")


class TestL8MemoryAudit(unittest.TestCase):
    def test_memory_accepts_only_sealed_packages_with_hash(self):
        s = SessionGateState(mode="generic")
        sealed = seal_observation_package({"observations": [_valid_obs()]}, s)
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(td)
            sid = m.seal_package(sealed)
            self.assertTrue(sid)
            bad = dict(sealed)
            bad.pop("package_hash")
            with self.assertRaises(SealError):
                m.seal_package(bad)

    def test_stored_seal_remains_observed_indicator(self):
        s = SessionGateState(mode="generic")
        sealed = seal_observation_package({"observations": [_valid_obs()]}, s)
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(td)
            sid = m.seal_package(sealed)
            import json
            loaded = json.loads((Path(td) / "seals" / f"{sid}.json").read_text())
            self.assertEqual(loaded["epistemic_status"], "observed_indicator")
            self.assertFalse(loaded["is_definitive_finding"])
            self.assertNotIn("deception_confirmed", json.dumps(loaded).lower())


if __name__ == "__main__":
    unittest.main()
