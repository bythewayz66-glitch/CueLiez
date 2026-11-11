"""Phase 7 live connectors (iceman, 0854): ingest validation + auditable GateError codes."""
import unittest

from cueliez.gates import (
    GateError,
    SessionGateState,
    seal_observation_package,
    validate_sealed_package_ingest,
)
from cueliez.ingest import build_ingested_package


def _obs():
    return [{"label": "indicator", "confidence": {"score": 0.4, "model_id": "m"}, "method": "m", "category": "behavioral", "evidence": {}}]


class MockConnectorIngest:
    """Mocked connector path: validates sealed package before attach (no live vendor)."""

    def __init__(self, *, auth_token=None, fail_network=False):
        self.auth_token = auth_token
        self.fail_network = fail_network
        self.attached = []

    def attach(self, package):
        if not self.auth_token:
            raise GateError("connector_auth_failed", "Connector auth token/config missing.")
        if self.fail_network:
            raise GateError("connector_network_error", "Mock network transport failure.")
        receipt = validate_sealed_package_ingest(package)
        self.attached.append(receipt)
        return receipt


class TestValidateSealedPackageIngest(unittest.TestCase):
    def test_valid_sealed_package(self):
        sealed = seal_observation_package({"observations": _obs()}, SessionGateState(mode="generic"))
        r = validate_sealed_package_ingest(sealed)
        self.assertTrue(r["ok"])
        self.assertEqual(r["package_hash"], sealed["package_hash"])

    def test_rejects_unsealed(self):
        with self.assertRaises(GateError) as ctx:
            validate_sealed_package_ingest({"observations": _obs()})
        self.assertEqual(ctx.exception.code, "ingest_not_sealed")

    def test_rejects_tampered_hash(self):
        sealed = seal_observation_package({"observations": _obs()}, SessionGateState(mode="generic"))
        sealed["observations"] = []
        with self.assertRaises(GateError) as ctx:
            validate_sealed_package_ingest(sealed)
        self.assertIn(ctx.exception.code, ("ingest_hash_mismatch", "connector_validation_failed"))

    def test_rejects_definitive_finding(self):
        from cueliez.gates import compute_package_hash
        sealed = seal_observation_package({"observations": _obs()}, SessionGateState(mode="generic"))
        bad = dict(sealed)
        bad["is_definitive_finding"] = True
        bad["package_hash"] = compute_package_hash(bad)  # internally consistent but policy-invalid
        with self.assertRaises(GateError) as ctx:
            validate_sealed_package_ingest(bad)
        self.assertEqual(ctx.exception.code, "ingest_epistemic_invalid")

    def test_mock_connector_success(self):
        pkg = build_ingested_package({"turns": [{"role": "interviewer", "text": "hello"}]})
        sealed = seal_observation_package(pkg, SessionGateState(mode="generic"))
        c = MockConnectorIngest(auth_token="env:TOKEN")
        r = c.attach(sealed)
        self.assertTrue(r["ok"])
        self.assertEqual(len(c.attached), 1)

    def test_mock_connector_auth_failure(self):
        sealed = seal_observation_package({"observations": _obs()}, SessionGateState(mode="generic"))
        c = MockConnectorIngest(auth_token=None)
        with self.assertRaises(GateError) as ctx:
            c.attach(sealed)
        self.assertEqual(ctx.exception.code, "connector_auth_failed")

    def test_mock_connector_network_failure(self):
        sealed = seal_observation_package({"observations": _obs()}, SessionGateState(mode="generic"))
        c = MockConnectorIngest(auth_token="x", fail_network=True)
        with self.assertRaises(GateError) as ctx:
            c.attach(sealed)
        self.assertEqual(ctx.exception.code, "connector_network_error")
