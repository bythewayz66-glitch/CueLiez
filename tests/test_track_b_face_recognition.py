"""Track B: REAL face recognition end-to-end (owner decision 2026-11-25).

Enrollment + OpenFace embedding matching with real photographs
(public-domain White House portraits in tests/fixtures/face/).
Skipped when the optional 'face' extra or the model files are absent —
the core stays stdlib-only and fails closed instead of faking a score.

Measured separation on this fixture (aligned embeddings, threshold 0.9):
same-person distances 0.49-0.75, different-person 1.15-1.25.
"""
import unittest
from pathlib import Path

from cueliez.gates import SessionGateState, record_modality_consent
from cueliez.observations.face_recognition import (
    FaceRecognitionUnavailable,
    FaceRecognizer,
    FaceTemplateStore,
    NoFaceDetected,
    distance_to_score,
    face_available,
)

ROOT = Path(__file__).resolve().parents[1]
FACE_DIR = ROOT / "tests" / "fixtures" / "face"
MODEL = FACE_DIR / "models" / "nn4.small2.v1.t7"
LANDMARKS = FACE_DIR / "models" / "lbfmodel.yaml"

FACE_READY = face_available() and MODEL.exists() and LANDMARKS.exists()


def _make_recognizer():
    return FaceRecognizer(MODEL, LANDMARKS)


@unittest.skipUnless(FACE_READY, "face extra / model files not present")
class TestRealFaceRecognition(unittest.TestCase):
    def test_enroll_and_match_held_out_same_person(self):
        rec = _make_recognizer()
        rec.enroll("obama", str(FACE_DIR / "obama.jpg"))
        rec.enroll("obama", str(FACE_DIR / "obama2.jpg"))
        # Held-out third photo of the same person must match.
        m = rec.match(str(FACE_DIR / "obama3.jpg"))
        self.assertTrue(m.matched, m.to_dict())
        self.assertEqual(m.subject_id, "obama")
        self.assertLess(m.distance, 0.9)
        self.assertGreater(m.score, 0.5)
        self.assertTrue(m.aligned)

    def test_different_person_does_not_match(self):
        rec = _make_recognizer()
        rec.enroll("obama", str(FACE_DIR / "obama.jpg"))
        rec.enroll("obama", str(FACE_DIR / "obama2.jpg"))
        for probe in ("biden.jpg", "biden2.jpg"):
            m = rec.match(str(FACE_DIR / probe))
            self.assertFalse(m.matched, f"{probe}: {m.to_dict()}")
            self.assertIsNone(m.subject_id)
            self.assertGreaterEqual(m.distance, 0.9)

    def test_no_enrollment_no_match_no_fake_score(self):
        rec = _make_recognizer()
        m = rec.match(str(FACE_DIR / "obama.jpg"))
        self.assertFalse(m.matched)
        self.assertIsNone(m.distance)
        self.assertEqual(m.score, 0.0)

    def test_no_face_detected(self):
        import tempfile
        from PIL import Image

        rec = _make_recognizer()
        rec.enroll("obama", str(FACE_DIR / "obama.jpg"))
        with tempfile.TemporaryDirectory() as td:
            blank = Path(td) / "blank.jpg"
            Image.new("RGB", (200, 200), color=(128, 128, 128)).save(blank)
            with self.assertRaises(NoFaceDetected):
                rec.match(str(blank))
            self.assertEqual(rec.detect_faces(str(blank)), [])

    def test_distance_to_score_is_a_similarity_not_a_probability(self):
        self.assertAlmostEqual(distance_to_score(0.0), 1.0)
        self.assertAlmostEqual(distance_to_score(2.0), 0.0)
        self.assertAlmostEqual(distance_to_score(0.6), 0.7)

    def test_template_store_requires_consent_record(self):
        rec = _make_recognizer()
        rec.enroll("obama", str(FACE_DIR / "obama.jpg"))
        store = FaceTemplateStore(rec)
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "templates.npz"
            with self.assertRaises(ValueError):
                store.save(p, consent_record={})
            info = store.save(p, consent_record={"attested_by": "officer-1", "jurisdiction": "jx-test"})
            self.assertEqual(info["subjects"], ["obama"])
            self.assertTrue(store.delete_subject("obama"))
            self.assertEqual(rec.enrolled_subjects(), [])
            loaded = store.load(p)
            self.assertEqual(loaded, ["obama"])
            m = rec.match(str(FACE_DIR / "obama2.jpg"))
            self.assertTrue(m.matched, m.to_dict())
            store.delete_all()
            self.assertEqual(rec.enrolled_subjects(), [])

    def test_face_recognition_observer_end_to_end(self):
        from cueliez.observations.gated import FaceRecognitionObserver

        rec = _make_recognizer()
        rec.enroll("obama", str(FACE_DIR / "obama.jpg"))
        rec.enroll("obama", str(FACE_DIR / "obama2.jpg"))
        obs = FaceRecognitionObserver(recognizer=rec)
        s = SessionGateState(mode="interrogation")
        record_modality_consent(s, "camera", attested_by="o", jurisdiction="jx", jurisdiction_approved=True)
        turns = [
            {"role": "subject", "text": "I was there.", "face_image": str(FACE_DIR / "obama3.jpg")},
            {"role": "subject", "text": "I was there.", "face_image": str(FACE_DIR / "biden.jpg")},
        ]
        res = obs.observe_with_context(turns, enabled=True, gate_state=s).to_dicts()
        matches = [o for o in res if o["label"] == "face_match_observed"]
        self.assertEqual(len(matches), 1, res)
        self.assertEqual(matches[0]["evidence"]["subject_id"], "obama")
        self.assertLess(matches[0]["evidence"]["embedding_distance"], 0.9)
        self.assertEqual(matches[0]["turn_index"], 0)
        # Disabled by default: no match observations at all.
        res2 = FaceRecognitionObserver(recognizer=rec).observe(turns).to_dicts()
        self.assertEqual(res2, [])
        # No camera consent: blocked even when enabled.
        s2 = SessionGateState(mode="interrogation")
        res3 = obs.observe_with_context(turns, enabled=True, gate_state=s2).to_dicts()
        self.assertEqual(res3, [])


class TestFaceRecognitionUnavailable(unittest.TestCase):
    def test_unavailable_without_dependency(self):
        if face_available():
            self.skipTest("face extra is installed in this interpreter")
        with self.assertRaises(FaceRecognitionUnavailable):
            FaceRecognizer("no-such-model.t7")


if __name__ == "__main__":
    unittest.main()
