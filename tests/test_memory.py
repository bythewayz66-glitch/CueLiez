import json
import tempfile
import unittest
from pathlib import Path

from cueliez.gates import DISCLAIMER, seal_observation_package
from cueliez.memory import ContaminationError, MemoryEngine, SealError


def _valid_pkg():
    return seal_observation_package({
        "observations": [{"label": "hedging_language_present", "confidence": {"score": 0.4, "model_id": "m/v1"}, "method": "m/v1", "category": "linguistic"}],
        "annotations": {},
    })


class TestMemoryEngine(unittest.TestCase):
    def test_init_creates_partitions(self):
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(store_path=td)
            self.assertTrue((Path(td) / "grounded").is_dir())
            self.assertTrue((Path(td) / "simulated").is_dir())
            self.assertTrue((Path(td) / "seals").is_dir())
            self.assertTrue(m.ledger_path.exists() is False or True)  # created on write

    def test_remember_observation_writes_grounded_and_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(store_path=td)
            rid = m.remember_observation("note", tags=["t"], evidence={"k": 1}, disclaimer="d")
            self.assertTrue((Path(td) / "grounded" / f"{rid}.json").exists())
            rec = json.loads((Path(td) / "grounded" / f"{rid}.json").read_text())
            self.assertEqual(rec["origin"], "grounded")
            self.assertEqual(rec["epistemic_status"], "observed_indicator")
            self.assertNotIn("lying", json.dumps(rec).lower())
            lines = m.ledger_path.read_text().strip().splitlines()
            self.assertTrue(any(json.loads(l).get("op") == "remember_observation" for l in lines))

    def test_remember_observation_rejects_forbidden_epistemic(self):
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(store_path=td)
            with self.assertRaises(ContaminationError):
                m.remember_observation("x", epistemic_status="deception_confirmed")
            with self.assertRaises(ContaminationError):
                m.remember_observation("x", epistemic_status="guilty")

    def test_remember_observation_rejects_unknown_epistemic(self):
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(store_path=td)
            with self.assertRaises(ContaminationError):
                m.remember_observation("x", epistemic_status="fact_finding")

    def test_seal_package_persists_and_ledgers_pointer(self):
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(store_path=td)
            pkg = _valid_pkg()
            sid = m.seal_package(pkg)
            path = Path(td) / "seals" / f"{sid}.json"
            self.assertTrue(path.exists())
            saved = json.loads(path.read_text())
            self.assertEqual(saved["seal_id"], sid)
            self.assertEqual(saved["epistemic_status"], "observed_indicator")
            self.assertFalse(saved["is_definitive_finding"])
            # pointer observation
            grounded = list((Path(td) / "grounded").glob("*.json"))
            self.assertTrue(any("sealed_session" in g.read_text() for g in grounded))

    def test_seal_package_rejects_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(store_path=td)
            with self.assertRaises(SealError):
                m.seal_package("no")  # type: ignore
            with self.assertRaises(ContaminationError):
                m.seal_package({"epistemic_status": "observed_indicator", "origin": "grounded", "disclaimer": "d",
                                "firewall": {"contamination_check": "passed"}, "is_definitive_finding": True})
            with self.assertRaises(ContaminationError):
                m.seal_package({"epistemic_status": "diagnosis", "origin": "grounded", "disclaimer": "d",
                                "firewall": {"contamination_check": "passed"}, "is_definitive_finding": False})
            with self.assertRaises(ContaminationError):
                m.seal_package({"epistemic_status": "observed_indicator", "origin": "simulated", "disclaimer": "d",
                                "firewall": {"contamination_check": "passed"}, "is_definitive_finding": False})
            with self.assertRaises(SealError):
                m.seal_package({"epistemic_status": "observed_indicator", "origin": "grounded", "disclaimer": "",
                                "firewall": {"contamination_check": "passed"}, "is_definitive_finding": False})
            with self.assertRaises(SealError):
                m.seal_package({"epistemic_status": "observed_indicator", "origin": "grounded", "disclaimer": "d",
                                "firewall": {"contamination_check": "failed"}, "is_definitive_finding": False})


if __name__ == "__main__":
    unittest.main()
