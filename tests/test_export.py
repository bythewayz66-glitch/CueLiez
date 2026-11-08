import json
import tempfile
import unittest
from pathlib import Path

from cueliez.delivery import attach_officer_cue_notes, cues_from_observations
from cueliez.export import (
    EXPORT_NOTICE,
    export_package_json,
    export_sealed_package,
    render_package_summary_html,
    render_package_summary_markdown,
)
from cueliez.gates import SessionGateState, record_consent, seal_observation_package

OBS = [
    {"label": "hedging_language_present", "confidence": {"score": 0.72, "model_id": "m/v1"},
     "category": "linguistic", "method": "m/v1", "cue": "Ask for specific details.", "turn_index": 1, "evidence": {"count": 3}},
    {"label": "possible_statement_conflict", "confidence": {"score": 0.65, "model_id": "m/v1"},
     "category": "consistency", "method": "m/v1", "cue": "Ask the subject to reconcile accounts.", "turn_index": 3,
     "evidence": {"turn_a": 1, "turn_b": 3}},
]


def sealed_pkg():
    s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
    record_consent(s, attested_by="officer-a")
    s.training_acknowledged = True
    s.training_version = "v1"
    pkg = {"observations": OBS, "annotations": {"mode": "interrogation", "cue_pack": "leg"}}
    return seal_observation_package(pkg, s)


class TestExportSurfaces(unittest.TestCase):
    def test_markdown_has_required_framing(self):
        md = render_package_summary_markdown(sealed_pkg())
        low = md.lower()
        self.assertIn("observed indicators and cues only", low)
        self.assertIn("disclaimer", low)
        self.assertIn("not a lie detector", low)  # canonical disclaimer
        self.assertIn("gate / consent status", low)
        self.assertIn("system-observed cues", low)
        self.assertNotIn("officer notes (human)", low)  # only when notes exist
        for bad in ("detects lies", "lie detection engine", "subject is lying", "truth score", "proves deception", "confirms lying"):
            self.assertNotIn(bad, low)

    def test_html_has_required_framing(self):
        h = render_package_summary_html(sealed_pkg())
        low = h.lower()
        self.assertIn("observed indicators and cues only", low)
        self.assertIn("disclaimer", low)
        self.assertIn("not a lie detector", low)  # canonical disclaimer
        self.assertIn("gate / consent status", low)
        for bad in ("detects lies", "lie detection engine", "subject is lying", "truth score", "proves deception", "confirms lying"):
            self.assertNotIn(bad, low)

    def test_export_json_preserves_notice(self):
        with tempfile.TemporaryDirectory() as td:
            path = export_package_json(sealed_pkg(), Path(td) / "p.json")
            data = json.loads(Path(path).read_text())
            self.assertIn("export_notice", data)
            self.assertEqual(data["epistemic_status"], "observed_indicator")
            self.assertFalse(data["is_definitive_finding"])

    def test_export_sealed_package_formats(self):
        with tempfile.TemporaryDirectory() as td:
            paths = export_sealed_package(sealed_pkg(), td, basename="case1", formats=["json", "md", "html"])
            self.assertTrue(Path(paths["json"]).exists())
            self.assertTrue(Path(paths["md"]).exists())
            self.assertTrue(Path(paths["html"]).exists())
            self.assertIn(EXPORT_NOTICE, Path(paths["md"]).read_text())
            self.assertIn("observed indicators and cues only", Path(paths["html"]).read_text().lower())

    def test_officer_notes_survive_into_export(self):
        cues = cues_from_observations(OBS)
        pkg = {"observations": OBS, "annotations": {"mode": "interrogation", "cue_pack": "leg"}}
        pkg = attach_officer_cue_notes(pkg, [{
            "cue_id": cues[0].cue_id, "action": "noted", "note": "Requested clarification on timeline.",
            "priority": cues[0].priority, "officer_id": "off1",
        }])
        s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
        record_consent(s, attested_by="officer-a")
        s.training_acknowledged = True
        s.training_version = "v1"
        sealed = seal_observation_package(pkg, s)
        md = render_package_summary_markdown(sealed)
        self.assertIn("Officer Notes (Human)", md)
        self.assertIn("not system findings", md.lower())
        self.assertIn("Requested clarification on timeline", md)
        self.assertIn(cues[0].cue_id, md)
        self.assertIn("off1", md)

    def test_e2e_note_attach_seal_export(self):
        cues = cues_from_observations(OBS)
        pkg = {"observations": OBS, "annotations": {"mode": "interrogation"}}
        pkg = attach_officer_cue_notes(pkg, [{"cue_id": cues[0].cue_id, "action": "acknowledged", "note": "Reviewed by officer."}])
        s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
        record_consent(s, attested_by="officer-a")
        s.training_acknowledged = True
        s.training_version = "v1"
        sealed = seal_observation_package(pkg, s)
        self.assertIn("officer_cue_notes", sealed)
        self.assertIn("gate_state", sealed)
        self.assertIn("package_hash", sealed)
        self.assertEqual(sealed["schema_version"], "1.0")
        with tempfile.TemporaryDirectory() as td:
            paths = export_sealed_package(sealed, td, cues=cues, observations=OBS)
            data = json.loads(Path(paths["json"]).read_text())
            self.assertIn("officer_cue_notes", data)
            self.assertEqual(data["officer_cue_notes"][0]["note"], "Reviewed by officer.")
            self.assertIn("Officer Notes (Human)", Path(paths["md"]).read_text())

    def test_export_resilient_without_gate_state_or_hash(self):
        pkg = {"product": "CueLiez", "observations": [], "disclaimer": "d"}
        md = render_package_summary_markdown(pkg, observations=[])
        self.assertIn("not provided", md.lower())
        h = render_package_summary_html(pkg, observations=[])
        self.assertIn("not provided", h.lower())

    def test_degrades_gracefully_with_no_cues(self):
        pkg = sealed_pkg()
        pkg["observations"] = []
        md = render_package_summary_markdown(pkg, observations=[])
        self.assertIn("No observation cues", md)
        with tempfile.TemporaryDirectory() as td:
            paths = export_sealed_package(pkg, td, observations=[], cues=[])
            self.assertTrue(Path(paths["json"]).exists())


if __name__ == "__main__":
    unittest.main()
