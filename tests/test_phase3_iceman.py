import unittest

from cueliez.gates import (
    BANNED_ANNOTATION_KEYS,
    GateError,
    SessionGateState,
    assert_not_sealed,
    is_sealed,
    record_consent,
    record_dual_acknowledge,
    seal_observation_package,
    verify_package_hash,
)
from cueliez.session import seal, start_session


def _valid_obs(label="indicator_present"):
    return {"label": label, "confidence": {"score": 0.5, "model_id": "m/v1"}, "method": "m/v1", "category": "behavioral", "evidence": {}}


class TestPhase3BannedContent(unittest.TestCase):
    def test_all_banned_annotation_keys_rejected(self):
        for key in sorted(BANNED_ANNOTATION_KEYS):
            with self.subTest(key=key):
                with self.assertRaises(GateError) as ctx:
                    seal_observation_package({"observations": [_valid_obs()], "annotations": {key: "x"}})
                self.assertEqual(ctx.exception.code, "contamination_attempt")

    def test_verdict_language_variants_rejected_in_observations(self):
        # seal-time verdict label rejection (observation contract)
        for label in ["lying", "lie", "deception_confirmed", "guilty", "truthful", "deceptive", "dishonest", "honest", "LYING", "Guilty"]:
            with self.subTest(label=label):
                obs = _valid_obs(label="ok")
                obs["label"] = label
                with self.assertRaises(GateError) as ctx:
                    seal_observation_package({"observations": [obs]})
                self.assertEqual(ctx.exception.code, "verdict_language")


class TestPhase3GateCodesAndHighStakes(unittest.TestCase):
    def test_interrogation_requires_consent_training(self):
        s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
        with self.assertRaises(GateError) as ctx:
            seal({"observations": [_valid_obs()]}, s)
        self.assertEqual(ctx.exception.code, "consent_required")
        record_consent(s, attested_by="att")
        with self.assertRaises(GateError) as ctx:
            seal({"observations": [_valid_obs()]}, s)
        self.assertEqual(ctx.exception.code, "training_required")
        s.training_acknowledged = True
        s.training_version = "v1"
        out = seal({"observations": [_valid_obs()]}, s)
        self.assertTrue(out["sealed"])

    def test_government_requires_dual_control_for_high_priority(self):
        s = SessionGateState(mode="government", intended_uses=["interview support"])
        record_consent(s, attested_by="att")
        s.training_acknowledged = True
        s.training_version = "v1"
        pkg = {"observations": [_valid_obs()], "cues": [{"cue_id": "c1", "priority": "high"}]}
        with self.assertRaises(GateError) as ctx:
            seal_observation_package(pkg, s)
        self.assertEqual(ctx.exception.code, "dual_control_incomplete")
        record_dual_acknowledge(s, "c1", "o1", "o2")
        out = seal_observation_package(pkg, s)
        self.assertTrue(out["sealed"])

    def test_prohibited_use_stable_code(self):
        s = SessionGateState(mode="interrogation", intended_uses=["lie_detector_claim"])
        record_consent(s, attested_by="att")
        s.training_acknowledged = True
        s.training_version = "v1"
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [_valid_obs()]}, s)
        self.assertEqual(ctx.exception.code, "prohibited_use")


class TestPhase3Immutability(unittest.TestCase):
    def test_reseal_refused(self):
        out = seal_observation_package({"observations": [_valid_obs()]}, SessionGateState(mode="generic"))
        self.assertTrue(is_sealed(out))
        with self.assertRaises(GateError) as ctx:
            seal_observation_package(out)
        self.assertEqual(ctx.exception.code, "package_sealed")

    def test_assert_not_sealed_and_hash_verification(self):
        out = seal_observation_package({"observations": [_valid_obs()]}, SessionGateState(mode="generic"))
        self.assertTrue(verify_package_hash(out))
        with self.assertRaises(GateError):
            assert_not_sealed(out)
