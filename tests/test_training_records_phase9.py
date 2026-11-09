"""Phase 9 minimal persistent training credential records (technical support)."""
import tempfile
import time
import unittest
from pathlib import Path

from cueliez.compliance.records import TrainingRecordStore
from cueliez.compliance.training import TrainingAcknowledgement, domain_training


class TestTrainingRecordsPhase9(unittest.TestCase):
    def test_issue_verify_revoke_and_ack(self):
        with tempfile.TemporaryDirectory() as td:
            store = TrainingRecordStore(Path(td) / "records.jsonl")
            mod = domain_training("gov")
            ack = TrainingAcknowledgement(
                module_id=mod.id,
                module_version=mod.version,
                operator_id="op-1",
                assessment_passed=True,
                completed_topics=list(mod.required_topics),
            )
            rec = store.issue(mod, ack, issued_by="trainer-1")
            self.assertTrue(rec.credential_id)
            v = store.verify(rec.credential_id)
            self.assertTrue(v["ok"])
            gate_ack = store.ack_for_gate(rec.credential_id)
            self.assertEqual(gate_ack.operator_id, "op-1")
            self.assertTrue(gate_ack.assessment_passed)
            store.revoke(rec.credential_id, by="admin", reason="test")
            v2 = store.verify(rec.credential_id)
            self.assertFalse(v2["ok"])
            self.assertEqual(v2["status"], "revoked")

    def test_expired_credential_not_valid(self):
        with tempfile.TemporaryDirectory() as td:
            store = TrainingRecordStore(Path(td) / "records.jsonl")
            mod = domain_training("leg")
            ack = TrainingAcknowledgement(module_id=mod.id, module_version=mod.version, operator_id="op-2", assessment_passed=True, completed_topics=list(mod.required_topics))
            rec = store.issue(mod, ack, expires_at=time.time() - 10)
            self.assertFalse(store.verify(rec.credential_id)["ok"])
            with self.assertRaises(ValueError):
                store.ack_for_gate(rec.credential_id)

    def test_invalid_ack_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            store = TrainingRecordStore(Path(td) / "records.jsonl")
            mod = domain_training("med")
            ack = TrainingAcknowledgement(module_id=mod.id, module_version=mod.version, operator_id="", assessment_passed=False)
            with self.assertRaises(ValueError):
                store.issue(mod, ack)


if __name__ == "__main__":
    unittest.main()

    def test_rbac_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            store = TrainingRecordStore(Path(td) / "records.jsonl", enforce_rbac=True, admin_actors=["admin1"])
            mod = domain_training("gov")
            ack = TrainingAcknowledgement(module_id=mod.id, module_version=mod.version, operator_id="op", assessment_passed=True, completed_topics=list(mod.required_topics))
            with self.assertRaises(PermissionError):
                store.issue(mod, ack, actor="intruder")
            rec = store.issue(mod, ack, actor="admin1")
            with self.assertRaises(PermissionError):
                store.revoke(rec.credential_id, actor="intruder")
            store.revoke(rec.credential_id, actor="admin1")
