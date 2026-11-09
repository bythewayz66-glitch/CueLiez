"""Phase 9 real signing/verification workflow tests."""
import os
import unittest

from cueliez.gates import SessionGateState, compute_package_hash, seal_observation_package
from cueliez.signing import hmac_sign_package, hmac_signer, verify_hmac_signature


def _obs():
    return [{"label": "indicator", "confidence": {"score": 0.4, "model_id": "m"}, "method": "m", "category": "behavioral", "evidence": {}}]


class TestSigningPhase9(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        os.environ["CUELIEZ_SIGNING_KEY"] = "test-key-material-0123456789"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_hmac_sign_and_verify(self):
        pkg = {"product": "CueLiez", "observations": _obs(), "epistemic_status": "observed_indicator", "is_definitive_finding": False}
        sig = hmac_sign_package(pkg)
        self.assertEqual(sig["type"], "hmac-sha256")
        self.assertEqual(sig["signed_hash"], compute_package_hash(pkg))
        pkg2 = dict(pkg)
        pkg2["package_signature"] = sig
        v = verify_hmac_signature(pkg2)
        self.assertTrue(v["ok"])

    def test_signature_detects_tamper(self):
        pkg = {"product": "CueLiez", "observations": _obs()}
        pkg["package_signature"] = hmac_sign_package(pkg)
        pkg["observations"] = []
        v = verify_hmac_signature(pkg)
        self.assertFalse(v["ok"])

    def test_seal_with_hmac_signer(self):
        sealed = seal_observation_package({"observations": _obs()}, SessionGateState(mode="generic"), signer=hmac_signer())
        self.assertIsInstance(sealed.get("package_signature"), dict)
        self.assertEqual(sealed["package_signature"].get("type"), "hmac-sha256")
        v = verify_hmac_signature(sealed)
        self.assertTrue(v["ok"])
        self.assertEqual(compute_package_hash(sealed), sealed["package_hash"])

    def test_verify_missing_key(self):
        os.environ.pop("CUELIEZ_SIGNING_KEY", None)
        pkg = {"product": "CueLiez", "observations": _obs()}
        pkg["package_signature"] = {"type": "hmac-sha256", "signed_hash": compute_package_hash(pkg), "sig": "abc"}
        v = verify_hmac_signature(pkg)
        self.assertFalse(v["ok"])
        self.assertEqual(v["reason"], "signing_key_missing")


if __name__ == "__main__":
    unittest.main()

    def test_verify_accepts_rotation_keys(self):
        old = b"oldkey-oldkey-oldkey-0001"
        new = b"newkey-newkey-newkey-0001"
        pkg = {"product": "CueLiez", "observations": _obs()}
        pkg["package_signature"] = hmac_sign_package(pkg, key=old)
        v = verify_hmac_signature(pkg, keys=[new, old])
        self.assertTrue(v["ok"])
