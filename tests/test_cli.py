import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TRANSCRIPT = [
    {"role": "subject", "text": "I think maybe I was around doing stuff, you know.", "response_latency_ms": 4500},
    {"role": "officer", "text": "Can you be specific?"},
    {"role": "subject", "text": "I did not do it, I swear honestly never."},
]


class TestCLI(unittest.TestCase):
    def run_cli(self, *args, input_obj=None):
        cmd = [sys.executable, "-m", "cueliez", *args]
        inp = json.dumps(input_obj).encode() if input_obj is not None else None
        return subprocess.run(cmd, input=inp, capture_output=True, timeout=60)

    def test_print_json_no_seal(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(TRANSCRIPT, f)
            path = f.name
        try:
            r = self.run_cli(path, "--no-seal", "--print-json")
            self.assertEqual(r.returncode, 0, r.stderr.decode())
            data = json.loads(r.stdout.decode())
            self.assertIn("observations", data)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_exports_with_gates(self):
        with tempfile.TemporaryDirectory() as td:
            tpath = Path(td) / "t.json"
            tpath.write_text(json.dumps(TRANSCRIPT))
            out = Path(td) / "out"
            r = self.run_cli(
                str(tpath), "--mode", "interrogation", "--consent", "--attested-by", "off1",
                "--training-ack", "--training-version", "v1", "--out-dir", str(out), "--basename", "pkg",
            )
            self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
            self.assertTrue((out / "pkg.json").exists())
            self.assertTrue((out / "pkg.summary.md").exists())
            self.assertTrue((out / "pkg.summary.html").exists())
            pkg = json.loads((out / "pkg.json").read_text())
            self.assertEqual(pkg["epistemic_status"], "observed_indicator")
            self.assertFalse(pkg["is_definitive_finding"])
            self.assertIn("disclaimer", pkg)

    def test_help_is_honest(self):
        r = self.run_cli("--help")
        self.assertEqual(r.returncode, 0)
        text = r.stdout.decode().lower()
        self.assertIn("observation", text)
        self.assertNotIn("lie detector", text)

    def test_non_generic_requires_gates_before_observe(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(TRANSCRIPT, f)
            path = f.name
        try:
            r = self.run_cli(path, "--mode", "interrogation", "--no-seal", "--print-json")
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stderr.decode())
            self.assertIn(err.get("error_code"), {"consent_required", "training_required"})
        finally:
            Path(path).unlink(missing_ok=True)

    def test_print_high_priority_cue_ids(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(TRANSCRIPT, f)
            path = f.name
        try:
            r = self.run_cli(path, "--no-seal", "--print-high-priority-cue-ids")
            self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
            data = json.loads(r.stdout.decode())
            self.assertIn("high_priority_cue_ids", data)
            self.assertIsInstance(data["high_priority_cue_ids"], list)
            self.assertIn("notice", data)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_transcript_loader_accepts_turns_and_speaker_aliases(self):
        payload = {"turns": [{"speaker": "subject", "text": "I think maybe I was around, you know."}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            path = f.name
        try:
            r = self.run_cli(path, "--no-seal", "--print-json")
            self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
            data = json.loads(r.stdout.decode())
            self.assertIn("observations", data)
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
