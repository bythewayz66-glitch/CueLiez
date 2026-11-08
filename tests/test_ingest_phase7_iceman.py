import json
import unittest
from pathlib import Path

from cueliez.gates import SessionGateState, seal_observation_package
from cueliez.ingest import build_ingested_package, load_transcript, transcript_source_hash


OWNER = Path(__file__).resolve().parents[1] / "docs" / "examples" / "owner_clean_interview.json"


class TestTranscriptIngestContract(unittest.TestCase):
    def test_load_transcript_path(self):
        t = load_transcript(OWNER)
        self.assertIsInstance(t, list)
        self.assertGreater(len(t), 0)

    def test_load_transcript_wrappers(self):
        t = load_transcript({"turns": [{"role": "interviewer", "text": "hi"}]})
        self.assertEqual(len(t), 1)
        t = load_transcript({"transcript": [{"text": "x"}]})
        self.assertEqual(len(t), 1)

    def test_build_ingested_package_has_source_artifact_and_seals(self):
        pkg = build_ingested_package(OWNER, session_id="s1")
        self.assertIn("observations", pkg)
        self.assertIn("source_artifact", pkg)
        self.assertEqual(pkg["source_artifact"]["type"], "transcript_json")
        self.assertTrue(pkg["source_artifact"]["transcript_sha256"])
        sealed = seal_observation_package(pkg, SessionGateState(mode="generic"))
        self.assertTrue(sealed["sealed"])
        self.assertIn("source_artifact", sealed)
        self.assertEqual(sealed["source_artifact"]["transcript_sha256"], pkg["source_artifact"]["transcript_sha256"])

    def test_transcript_source_hash_stable(self):
        t = load_transcript(OWNER)
        self.assertEqual(transcript_source_hash(t), transcript_source_hash(t))

    def test_clinical_therapy_gate_rules_apply(self):
        pkg = build_ingested_package(OWNER)
        for mode in ("clinical", "therapy"):
            s = SessionGateState(mode=mode, intended_uses=["interview support"])
            with self.assertRaises(Exception):
                seal_observation_package(pkg, s)
