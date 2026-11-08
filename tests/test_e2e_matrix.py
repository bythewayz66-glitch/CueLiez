import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cueliez.delivery import attach_officer_cue_notes, cues_from_observations
from cueliez.export import export_sealed_package, render_package_summary_markdown
from cueliez.gates import GateError, SessionGateState, record_consent, seal_observation_package

OBS = [
    {"label": "hedging_language_present", "confidence": {"score": 0.72, "model_id": "m/v1"},
     "category": "linguistic", "method": "m/v1", "cue": "Ask for specific details.", "turn_index": 1, "evidence": {"count": 3}},
    {"label": "possible_statement_conflict", "confidence": {"score": 0.65, "model_id": "m/v1"},
     "category": "consistency", "method": "m/v1", "cue": "Ask the subject to reconcile accounts.", "turn_index": 3,
     "evidence": {"turn_a": 1, "turn_b": 3}},
]


class TestE2EMatrix(unittest.TestCase):
    def test_generic_observe_note_seal_export(self):
        cues = cues_from_observations(OBS)
        pkg = {"observations": OBS, "annotations": {"mode": "generic"}}
        pkg = attach_officer_cue_notes(pkg, [{"cue_id": cues[0].cue_id, "action": "noted", "note": "Human note."}])
        sealed = seal_observation_package(pkg, SessionGateState(mode="generic"))
        self.assertIn("officer_cue_notes", sealed)
        self.assertIn("package_hash", sealed)
        with tempfile.TemporaryDirectory() as td:
            paths = export_sealed_package(sealed, td, cues=cues, observations=OBS)
            self.assertTrue(Path(paths["json"]).exists())
            self.assertIn("Human note", Path(paths["md"]).read_text())

    def test_interrogation_missing_consent_fails(self):
        s = SessionGateState(mode="interrogation")
        s.training_acknowledged = True
        s.training_version = "v1"
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": OBS}, s)
        self.assertEqual(ctx.exception.code, "consent_required")

    def test_interrogation_with_consent_succeeds(self):
        s = SessionGateState(mode="interrogation")
        record_consent(s, attested_by="officer-a")
        s.training_acknowledged = True
        s.training_version = "v1"
        sealed = seal_observation_package({"observations": OBS}, s)
        self.assertEqual(sealed["epistemic_status"], "observed_indicator")

    def test_sealed_package_rejects_further_note_attach(self):
        s = SessionGateState(mode="interrogation")
        record_consent(s, attested_by="officer-a")
        s.training_acknowledged = True
        s.training_version = "v1"
        sealed = seal_observation_package({"observations": OBS}, s)
        with self.assertRaises(Exception):
            attach_officer_cue_notes(sealed, {"cue_id": "c1", "note": "late"})

    def test_high_priority_ids_appear_in_export_when_present(self):
        cues = cues_from_observations(OBS)
        hi = [c.cue_id for c in cues if c.priority in {"high", "critical"}]
        self.assertTrue(hi, "fixture should produce a high/critical cue for this test")
        sealed = seal_observation_package({"observations": OBS}, SessionGateState(mode="generic"))
        md = render_package_summary_markdown(sealed, cues=cues, observations=OBS)
        self.assertIn(hi[0], md)
        self.assertIn("high-priority cue id", md.lower())


if __name__ == "__main__":
    unittest.main()
