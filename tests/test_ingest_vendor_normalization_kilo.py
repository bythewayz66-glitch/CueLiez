"""Phase 7 live connectors (kilo): vendor/common transcript ingest normalization.

Mocked sample payloads only (no live vendor access). Normalizes to canonical turns.
"""
import unittest

from cueliez.ingest import canonicalize_turn, load_transcript, normalize_transcript, validate_transcript_turns
from cueliez.observations import default_runner


class TestIngestVendorNormalizationKilo(unittest.TestCase):
    def test_canonicalize_common_aliases(self):
        t = canonicalize_turn({"speaker": "Officer A", "utterance": "State your name.", "start_time": 1.2, "end_time": 3.4})
        self.assertEqual(t["role"], "interviewer")
        self.assertEqual(t["text"], "State your name.")
        self.assertEqual(t["start_time"], 1.2)
        t2 = canonicalize_turn({"speakerRole": "suspect", "content": "I do not know."})
        self.assertEqual(t2["role"], "subject")
        self.assertEqual(t2["text"], "I do not know.")

    def test_words_array_text(self):
        t = canonicalize_turn({"role": "subject", "words": [{"word": "I"}, {"word": "left"}, {"word": "early"}]})
        self.assertEqual(t["text"], "I left early")

    def test_vendor_like_wrappers_and_payloads(self):
        # Mocked/common shapes (not vendor-proprietary API claims)
        axon_like = {
            "utterances": [
                {"speaker": "interviewer", "text": "When did you arrive?", "start": 0.0, "end": 1.5},
                {"speaker": "subject", "text": "Maybe around nine.", "start": 2.0, "end": 4.0},
            ]
        }
        rms_like = {
            "segments": [
                {"speaker_type": "officer", "body": "Where were you?"},
                {"speaker_type": "witness", "body": "I was at home."},
            ]
        }
        casecracker_like = [
            {"participant": "Interviewer", "message": "Tell me what happened."},
            {"participant": "Respondent", "message": "I am not sure."},
        ]
        for payload, n in ((axon_like, 2), (rms_like, 2), (casecracker_like, 2)):
            turns = load_transcript(payload)
            self.assertEqual(len(turns), n)
            for turn in turns:
                self.assertIn("role", turn)
                self.assertIn("text", turn)

    def test_normalized_transcripts_pass_runner(self):
        payload = {"transcript": [
            {"speaker": "interviewer", "text": "What happened?"},
            {"speaker": "subject", "text": "I think maybe I left early, I do not remember exactly."},
        ]}
        turns = normalize_transcript(payload)
        pkg = default_runner().build_package(turns)
        self.assertIsInstance(pkg.get("observations"), list)

    def test_validation_rejects_invalid_root(self):
        with self.assertRaises(ValueError):
            validate_transcript_turns("not a transcript structure")
        self.assertEqual(validate_transcript_turns(None), [])
        # null turns skipped
        out = validate_transcript_turns([{"text": "hi"}, None, {"speaker": "x", "body": "ok"}])
        self.assertEqual(len(out), 2)

    def test_preserves_useful_metadata(self):
        turns = normalize_transcript([{"speaker": "subject", "text": "hi", "speakerId": "S1", "start_ms": 100, "asr_confidence": 0.9}])
        self.assertEqual(turns[0].get("speakerId"), "S1")
        self.assertEqual(turns[0].get("start_ms"), 100)


if __name__ == "__main__":
    unittest.main()
