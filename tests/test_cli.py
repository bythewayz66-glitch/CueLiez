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

ROOT = Path(__file__).resolve().parents[1]
OWNER = {
    "clean": ROOT / "docs/examples/owner_clean_interview.json",
    "conflict": ROOT / "docs/examples/owner_conflict_interview.json",
    "hedging": ROOT / "docs/examples/owner_hedging_interview.json",
}

# Verdict/banned claim phrases that must not appear as assertions in outputs.
# (The required disclaimer legitimately contains "not a lie detector"/"not a polygraph"; exports may include it.)
FORBIDDEN_CLAIM_PHRASES = (
    "subject is lying",
    "subject is deceptive",
    "confirms lying",
    "proves deception",
    "proves lying",
    "truth detector",
    "detects lies",
    "lie detection result",
    "guilty finding",
    "diagnosed as",
)


def _assert_no_forbidden_claims(testcase, text, *, allow_disclaimer=False):
    low = text.lower()
    if allow_disclaimer:
        # Remove the canonical disclaimer block's known negated references so we can still catch positive claims.
        low = low.replace("not a lie detector, not a medical device, and not a polygraph", "")
        low = low.replace("not a lie detector", "")
    for bad in FORBIDDEN_CLAIM_PHRASES:
        testcase.assertNotIn(bad, low, f"forbidden claim phrase {bad!r} found in output")


class TestCLIOwnerTranscripts(unittest.TestCase):
    def run_cli(self, *args):
        env = dict(__import__("os").environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        cmd = [sys.executable, "-m", "cueliez", *args]
        return subprocess.run(cmd, capture_output=True, timeout=120, env=env, cwd=str(ROOT))

    def test_owner_transcripts_show_cues_generic_no_seal(self):
        for name, path in OWNER.items():
            with self.subTest(transcript=name):
                r = self.run_cli(str(path), "--mode", "generic", "--show-cues", "--no-seal")
                self.assertEqual(r.returncode, 0, (name, r.stderr.decode(), r.stdout.decode()))
                out = r.stdout.decode() + "\n" + r.stderr.decode()
                self.assertIn("does not determine credibility or produce findings", out)
                _assert_no_forbidden_claims(self, out, allow_disclaimer=True)
                if '"cue_count": 0' not in out and "No observation cues" not in out:
                    self.assertIn("Source", out)

    def test_owner_transcripts_sealed_exports_and_hash(self):
        from cueliez.gates import compute_package_hash

        for name, path in OWNER.items():
            with self.subTest(transcript=name):
                with tempfile.TemporaryDirectory() as td:
                    out = Path(td) / "out"
                    r = self.run_cli(
                        str(path), "--mode", "generic", "--show-cues",
                        "--out-dir", str(out), "--basename", f"owner_{name}",
                    )
                    self.assertEqual(r.returncode, 0, (name, r.stderr.decode(), r.stdout.decode()))
                    for ext, fn in (("json", f"owner_{name}.json"), ("md", f"owner_{name}.summary.md"), ("html", f"owner_{name}.summary.html")):
                        self.assertTrue((out / fn).exists(), (name, ext, list(out.iterdir())))
                    pkg = json.loads((out / f"owner_{name}.json").read_text(encoding="utf-8"))
                    self.assertTrue(pkg.get("sealed"))
                    self.assertIn("gate_state", pkg)
                    ph = str(pkg.get("package_hash") or "")
                    self.assertRegex(ph, r"^[0-9a-f]{64}$")
                    self.assertEqual(pkg.get("epistemic_status"), "observed_indicator")
                    self.assertFalse(pkg.get("is_definitive_finding"))
                    self.assertIn("disclaimer", pkg)
                    # Hash determinism on the exported structure (iceman owns canonicalization contract).
                    self.assertEqual(compute_package_hash(pkg), compute_package_hash(json.loads(json.dumps(pkg))))
                    md = (out / f"owner_{name}.summary.md").read_text(encoding="utf-8")
                    html = (out / f"owner_{name}.summary.html").read_text(encoding="utf-8")
                    _assert_no_forbidden_claims(self, md, allow_disclaimer=True)
                    _assert_no_forbidden_claims(self, html, allow_disclaimer=True)
                    obs = pkg.get("observations") or []
                    if obs:
                        self.assertTrue(
                            ("Source (transcript)" in md) or ("Source (T" in md) or ("transcript" in md.lower()),
                            f"{name}: expected source/transcript context in markdown when cues exist",
                        )


class TestCLIStreamTurns(unittest.TestCase):
    def run_cli(self, *args, input_text=None):
        env = dict(__import__("os").environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        cmd = [sys.executable, "-m", "cueliez", *args]
        inp = input_text.encode() if isinstance(input_text, str) else input_text
        return subprocess.run(cmd, input=inp, capture_output=True, timeout=120, env=env, cwd=str(ROOT))

    def test_stream_turns_emits_new_cues_and_final_package(self):
        ndjson = (
            '{"role":"subject","text":"I arrived at eight."}\n'
            '{"role":"officer","text":"And when did you leave?"}\n'
            '{"role":"subject","text":"I think maybe I left around stuff, you know."}\n'
        )
        r = self.run_cli("-", "--mode", "generic", "--stream-turns", "--no-seal", input_text=ndjson)
        self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
        lines = [ln for ln in r.stdout.decode().splitlines() if ln.strip()]
        # stream events + final JSON
        events = []
        for ln in lines:
            try:
                events.append(json.loads(ln))
            except Exception:
                pass
        self.assertTrue(any(e.get("event") == "stream_start" and e.get("subject_visible") is False for e in events))
        self.assertTrue(any("notice" in e and "does not determine credibility" in str(e.get("notice")) for e in events))
        # should have surfaced cues or turn events
        self.assertTrue(any(e.get("event") in ("new_cues", "turn", "stream_end") for e in events))
        out_text = r.stdout.decode().lower()
        self.assertNotIn("subject is lying", out_text)
        self.assertNotIn("truth detector", out_text)
        # final package-like object present (may be pretty-printed across lines)
        self.assertIn('"observations"', r.stdout.decode())

    def test_stream_turns_generic_gated_modes_still_fail_closed(self):
        ndjson = '{"role":"subject","text":"hello"}\n'
        r = self.run_cli("-", "--mode", "interrogation", "--stream-turns", "--no-seal", input_text=ndjson)
        self.assertNotEqual(r.returncode, 0)
        err = json.loads(r.stderr.decode())
        self.assertIn(err.get("error_code"), {"consent_required", "training_required"})
