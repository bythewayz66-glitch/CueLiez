import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

OWNER_TRANSCRIPTS = [
    "docs/examples/owner_clean_interview.json",
    "docs/examples/owner_conflict_interview.json",
    "docs/examples/owner_hedging_interview.json",
]

FORBIDDEN = ["lie detector", "truth score", "polygraph", "guilty", "diagnosis"]


class TestHardeningOwnerTranscriptsGlyph(unittest.TestCase):
    def run_cli(self, *args):
        cmd = [sys.executable, "-m", "cueliez", *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    def test_owner_transcripts_run_and_seal(self):
        root = Path(__file__).resolve().parents[1]
        for rel in OWNER_TRANSCRIPTS:
            tpath = root / rel
            self.assertTrue(tpath.exists(), rel)
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "out"
                r = self.run_cli(str(tpath), "--mode", "generic", "--out-dir", str(out), "--basename", "pkg")
                self.assertEqual(r.returncode, 0, f"{rel}: {r.stderr}\n{r.stdout}")
                pkg_path = out / "pkg.json"
                self.assertTrue(pkg_path.exists(), rel)
                pkg = json.loads(pkg_path.read_text())
                self.assertEqual(pkg["epistemic_status"], "observed_indicator")
                self.assertFalse(pkg["is_definitive_finding"])
                self.assertIn("disclaimer", pkg)
                self.assertIn("package_hash", pkg)
                # wording check on rendered output
                rendered = (r.stdout + r.stderr).lower()
                for term in FORBIDDEN:
                    self.assertNotIn(term, rendered, f"{rel}: forbidden term '{term}'")

    def test_owner_transcripts_no_seal_show_cues(self):
        root = Path(__file__).resolve().parents[1]
        for rel in OWNER_TRANSCRIPTS:
            tpath = root / rel
            r = self.run_cli(str(tpath), "--mode", "generic", "--no-seal", "--show-cues")
            self.assertEqual(r.returncode, 0, f"{rel}: {r.stderr}\n{r.stdout}")
            rendered = (r.stdout + r.stderr).lower()
            for term in FORBIDDEN:
                self.assertNotIn(term, rendered, f"{rel}: forbidden term '{term}'")