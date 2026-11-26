"""Track A regression tests (Nov 25 2026): sealed-package hash on export,
dashboard XSS, modality-consent gaps (a)-(f), malformed NDJSON streaming,
and the separate demographic-inference gate (owner clarification Nov 25 2026).

Owner rule: demographic inference stays behind its OWN separate gate — it is
never folded into general modality consent.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

from cueliez.delivery.dashboard import LiveDashboardServer
from cueliez.export import export_sealed_package
from cueliez.gates import (
    DEMOGRAPHIC_INFERENCE_WARNING,
    GateError,
    SessionGateState,
    filter_observations_by_consent,
    has_demographic_inference_consent,
    has_modality_consent,
    record_consent,
    record_demographic_inference_consent,
    record_modality_consent,
    require_demographic_inference_consent,
    require_gated_modality,
    require_modality_consent_for_observations,
    revoke_demographic_inference_consent,
    revoke_modality_consent,
    seal_observation_package,
    verify_package_hash,
)
from tests import js_dom_harness as H

ROOT = Path(__file__).resolve().parents[1]
MALICIOUS_CUE = "<img src=x onerror=alert(1)>"


def _obs(label="hesitation_marker_present", category="behavioral",
         method="m/v1", score=0.5, evidence=None):
    return {"label": label, "confidence": {"score": score, "model_id": "m/v1"},
            "method": method, "category": category, "evidence": evidence or {}}


def _ready_state(mode="generic"):
    s = SessionGateState(mode=mode, intended_uses=["interview support"])
    return s


def _modal_state(modality, jurisdiction="J"):
    s = _ready_state()
    record_modality_consent(s, modality, attested_by="officer-a", jurisdiction=jurisdiction)
    return s


class TestExportedPackageHashVerifies(unittest.TestCase):
    """Task 1: export adds exported_at/export_notice AFTER sealing; the
    canonical hash must exclude those export-added fields."""

    def test_exported_package_verifies(self):
        s = SessionGateState(mode="interrogation", intended_uses=["interview support"])
        record_consent(s, attested_by="officer-a")
        s.training_acknowledged = True
        s.training_version = "v1"
        sealed = seal_observation_package({"observations": [_obs()]}, s)
        self.assertTrue(verify_package_hash(sealed))
        with tempfile.TemporaryDirectory() as td:
            paths = export_sealed_package(sealed, td, basename="sealed_package")
            exported = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
            self.assertIn("exported_at", exported)
            self.assertIn("export_notice", exported)
            # The exported file must still verify — this failed before the fix.
            self.assertTrue(verify_package_hash(exported), "exported sealed package must verify")

    def test_verify_package_cli_returns_hash_ok(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            r = subprocess.run(
                [sys.executable, "-m", "cueliez", "docs/examples/conflict_transcript.json",
                 "--pack", "leg", "--mode", "interrogation", "--consent",
                 "--consent-attester", "officer-a", "--training-version", "v1",
                 "--out-dir", str(out), "--basename", "sealed_package"],
                capture_output=True, timeout=120, env=env, cwd=str(ROOT))
            self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
            r = subprocess.run(
                [sys.executable, "-m", "cueliez", "--verify-package", str(out / "sealed_package.json")],
                capture_output=True, timeout=60, env=env, cwd=str(ROOT))
            self.assertEqual(r.returncode, 0, r.stdout.decode() + r.stderr.decode())
            self.assertTrue(json.loads(r.stdout.decode())["hash_ok"])


class TestDashboardXssRegression(unittest.TestCase):
    """Task 2: a cue containing <img src=x onerror=alert(1)> must never
    become markup. The dashboard renders cue text via DOM nodes/textContent."""

    def test_malicious_cue_never_becomes_markup(self):
        if H.NODE is None:
            self.skipTest("node not installed; client-side rendering test needs it")
        with LiveDashboardServer(host="127.0.0.1", port=0) as srv:
            with urllib.request.urlopen(srv.url) as r:
                html = r.read().decode("utf-8")
        scripts = H.extract_inline_scripts(html)
        self.assertEqual(len(scripts), 1)
        cue = {"cue_id": "c-mal", "message": MALICIOUS_CUE, "priority": "high",
               "score": 0.5, "category": "linguistic", "turn_index": 1,
               "source_quotes": [{"quote": MALICIOUS_CUE, "turn_index": 1}]}
        with tempfile.TemporaryDirectory() as td:
            res = H.run_script(scripts[0], ids=["status", "cues"],
                               fetch_json={"cues": [cue]}, tmp_dir=Path(td))
        self.assertEqual(res["errors"], [])
        self.assertEqual(res["sinks"], [], "cue text must never reach a raw-HTML sink")
        self.assertIsNone(res["pwned"])
        self.assertFalse(any(el["tag"] == "img" for el in res["created"]),
                         "malicious cue must not create an <img> element")
        violations, text = H.analyse(res, {"div", "span", "p"})
        self.assertEqual(violations, [])
        # Payload is displayed as inert text, not executed markup.
        self.assertIn(MALICIOUS_CUE, text)

    def test_served_dashboard_has_no_raw_html_sinks(self):
        with LiveDashboardServer(host="127.0.0.1", port=0) as srv:
            with urllib.request.urlopen(srv.url) as r:
                html = r.read().decode("utf-8")
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            self.assertNotIn(sink, html)
        self.assertIn("textContent", html)


class TestModalityConsentGaps(unittest.TestCase):
    """Task 3 (a)-(c) and (f), plus the separate demographic gate."""

    def test_3a_statewide_approval_does_not_override_per_modality_refusal(self):
        s = _ready_state()
        record_modality_consent(s, "camera", attested_by="officer-a",
                                jurisdiction="J", jurisdiction_approved=False)
        s.jurisdiction_approved = True  # blanket state-wide approval
        with self.assertRaises(GateError) as ctx:
            require_gated_modality(s, "camera")
        self.assertEqual(ctx.exception.code, "jurisdiction_approval_required")

    def test_3a_per_modality_approval_passes_without_statewide_flag(self):
        s = _modal_state("audio_features")
        self.assertFalse(s.jurisdiction_approved)
        require_gated_modality(s, "audio_features")

    def test_3b_record_modality_consent_does_not_set_statewide_flag(self):
        s = _ready_state()
        record_modality_consent(s, "audio_features", attested_by="officer-a", jurisdiction="J")
        self.assertFalse(s.jurisdiction_approved,
                         "recording per-modality consent must not flip state.jurisdiction_approved")
        self.assertTrue(has_modality_consent(s, "audio_features"))

    def test_3b_explicit_opt_in_can_set_statewide_flag(self):
        s = _ready_state()
        record_modality_consent(s, "audio_features", attested_by="officer-a",
                                jurisdiction="J", approve_state_jurisdiction=True)
        self.assertTrue(s.jurisdiction_approved)

    def test_3c_revoke_modality_consent(self):
        s = _modal_state("camera")
        record = revoke_modality_consent(s, "camera", attested_by="officer-b")
        self.assertTrue(record["consented"])
        self.assertEqual(record["attested_by"], "officer-a")
        self.assertNotIn("camera", s.modality_consents)
        with self.assertRaises(GateError) as ctx:
            require_gated_modality(s, "camera")
        self.assertEqual(ctx.exception.code, "modality_consent_required")
        with self.assertRaises(GateError) as ctx:
            revoke_modality_consent(s, "camera", attested_by="officer-b")
        self.assertEqual(ctx.exception.code, "modality_consent_not_found")

    def test_3c_revoke_requires_attester(self):
        s = _modal_state("camera")
        with self.assertRaises(GateError) as ctx:
            revoke_modality_consent(s, "camera", attested_by="  ")
        self.assertEqual(ctx.exception.code, "consent_attester_required")

    def test_3f_seal_requires_modality_consent_for_feature_observations(self):
        cases = [
            ("prosody", "cueliez.observations.prosody.variability_shift/v1", "audio_features"),
            ("visual", "cueliez.observations.visual.gaze_pattern/v1", "camera"),
            ("physiological", "cueliez.observations.physiological.heart_rate_shift/v1", "wearable"),
        ]
        for category, method, modality in cases:
            with self.subTest(category=category):
                s = _ready_state()
                with self.assertRaises(GateError) as ctx:
                    seal_observation_package(
                        {"observations": [_obs(label="feature_shift_observed", category=category, method=method)]}, s)
                self.assertEqual(ctx.exception.code, "modality_consent_required")
                # Consent for a DIFFERENT modality does not satisfy it.
                other = "camera" if modality != "camera" else "audio_features"
                record_modality_consent(s, other, attested_by="officer-a", jurisdiction="J")
                with self.assertRaises(GateError):
                    seal_observation_package(
                        {"observations": [_obs(label="feature_shift_observed", category=category, method=method)]}, s)
                record_modality_consent(s, modality, attested_by="officer-a", jurisdiction="J")
                out = seal_observation_package(
                    {"observations": [_obs(label="feature_shift_observed", category=category, method=method)]}, s)
                self.assertTrue(out["sealed"])

    def test_3f_seal_multimodal_convergence_inherits_gated_categories(self):
        s = _ready_state()
        obs = _obs(label="multi_indicator_convergence_observed", category="multimodal",
                   method="cueliez.observations.multimodal.convergence/v1",
                   evidence={"categories": ["linguistic", "prosody"], "category_count": 2})
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [obs]}, s)
        self.assertEqual(ctx.exception.code, "modality_consent_required")
        record_modality_consent(s, "audio_features", attested_by="officer-a", jurisdiction="J")
        out = seal_observation_package({"observations": [obs]}, s)
        self.assertTrue(out["sealed"])

    def test_3f_text_observations_seal_without_modality_consent(self):
        out = seal_observation_package({"observations": [_obs()]}, _ready_state())
        self.assertTrue(out["sealed"])

    def test_filter_drops_unconsented_feature_observations(self):
        s = _ready_state()
        obs = [_obs(category="linguistic"),
               _obs(label="prosodic_variability_shift_observed", category="prosody",
                    method="cueliez.observations.prosody.variability_shift/v1"),
               _obs(label="gaze_pattern_shift_observed", category="visual",
                    method="cueliez.observations.visual.gaze_pattern/v1")]
        kept = filter_observations_by_consent(obs, s)
        self.assertEqual([o["category"] for o in kept], ["linguistic"])
        record_modality_consent(s, "audio_features", attested_by="officer-a", jurisdiction="J")
        kept = filter_observations_by_consent(obs, s)
        self.assertEqual([o["category"] for o in kept], ["linguistic", "prosody"])


class TestDemographicInferenceSeparateGate(unittest.TestCase):
    """Owner clarification Nov 25 2026: demographic inference has its OWN
    gate — separate record, separate consent function, separate revocation.
    General modality consent must never enable it."""

    def test_general_modality_consent_does_not_enable_demographic_inference(self):
        s = _ready_state()
        for modality in ("audio_features", "camera", "wearable"):
            record_modality_consent(s, modality, attested_by="officer-a", jurisdiction="J")
        self.assertIsNone(s.demographic_inference_consent)
        self.assertFalse(has_demographic_inference_consent(s))
        with self.assertRaises(GateError) as ctx:
            require_demographic_inference_consent(s)
        self.assertEqual(ctx.exception.code, "demographic_inference_consent_required")

    def test_demographic_inference_requires_own_explicit_consent(self):
        s = _ready_state()
        # Without acknowledging the bias/admissibility warning, no record.
        with self.assertRaises(GateError) as ctx:
            record_demographic_inference_consent(s, attested_by="officer-a", jurisdiction="J")
        self.assertEqual(ctx.exception.code, "demographic_inference_warning_not_acknowledged")
        self.assertIn("bias", DEMOGRAPHIC_INFERENCE_WARNING.lower())
        self.assertIn("admissibility", DEMOGRAPHIC_INFERENCE_WARNING.lower())
        record_demographic_inference_consent(
            s, attested_by="officer-a", jurisdiction="J", bias_warning_acknowledged=True)
        self.assertTrue(has_demographic_inference_consent(s))
        require_demographic_inference_consent(s)
        # Recording it did not create any modality consent.
        self.assertEqual(s.modality_consents, {})

    def test_demographic_inference_revocation(self):
        s = _ready_state()
        record_demographic_inference_consent(
            s, attested_by="officer-a", jurisdiction="J", bias_warning_acknowledged=True)
        record = revoke_demographic_inference_consent(s, attested_by="officer-b")
        self.assertTrue(record["consented"])
        self.assertIsNone(s.demographic_inference_consent)
        with self.assertRaises(GateError) as ctx:
            require_demographic_inference_consent(s)
        self.assertEqual(ctx.exception.code, "demographic_inference_consent_required")
        with self.assertRaises(GateError) as ctx:
            revoke_demographic_inference_consent(s, attested_by="officer-b")
        self.assertEqual(ctx.exception.code, "demographic_inference_consent_not_found")

    def test_seal_demographic_observation_requires_separate_consent(self):
        s = _ready_state()
        for modality in ("audio_features", "camera", "wearable"):
            record_modality_consent(s, modality, attested_by="officer-a", jurisdiction="J")
        obs = _obs(label="demographic_attribute_inferred", category="demographic",
                   method="cueliez.observations.demographic/inference/v1")
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [obs]}, s)
        self.assertEqual(ctx.exception.code, "demographic_inference_consent_required")
        record_demographic_inference_consent(
            s, attested_by="officer-a", jurisdiction="J", bias_warning_acknowledged=True)
        out = seal_observation_package({"observations": [obs]}, s)
        self.assertTrue(out["sealed"])


def _cli_env():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return env


def _run_cli(args, input_text=None):
    inp = input_text.encode() if isinstance(input_text, str) else input_text
    return subprocess.run([sys.executable, "-m", "cueliez", *args], input=inp,
                          capture_output=True, timeout=120, env=_cli_env(), cwd=str(ROOT))


# Prosody feature turns: 3x pitch_variance 10 then 1x 80 -> a prosody
# observation fires under the full runner; text is neutral on purpose.
PROSODY_TURNS = [
    {"role": "subject", "text": "answer", "prosody": {"pitch_variance": 10.0}},
    {"role": "subject", "text": "answer", "prosody": {"pitch_variance": 10.0}},
    {"role": "subject", "text": "answer", "prosody": {"pitch_variance": 10.0}},
    {"role": "subject", "text": "answer", "prosody": {"pitch_variance": 80.0}},
]
PROSODY_NDJSON = "".join(json.dumps(t) + "\n" for t in PROSODY_TURNS)


def _events(stdout_text):
    out = []
    for ln in stdout_text.splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


def _final_package(stdout_text):
    """Parse the pretty-printed final package JSON at the end of stream output."""
    lines = stdout_text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip() == "{"]
    assert starts, "no pretty-printed final package found in stream output"
    return json.loads("\n".join(lines[starts[-1]:]))


def _cue_categories(events):
    cats = set()
    for e in events:
        for c in e.get("cues", []):
            cats.add(c.get("category"))
    return cats


class TestModalityConsentCli(unittest.TestCase):
    """Task 3 (d): --modality-consent / --modality-attester CLI flag."""

    def test_modality_consent_flag_enables_prosody(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(PROSODY_TURNS, f)
            path = f.name
        try:
            r = _run_cli([path, "--runner", "full", "--no-seal", "--print-json",
                          "--modality-consent", "audio_features",
                          "--modality-attester", "officer-a", "--jurisdiction", "J"])
            self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
            data = json.loads(r.stdout.decode())
            self.assertTrue(any(o.get("category") == "prosody" for o in data["observations"]),
                            "prosody observation must be present with audio_features consent")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_modality_consent_flag_requires_attester(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(PROSODY_TURNS, f)
            path = f.name
        try:
            r = _run_cli([path, "--runner", "full", "--no-seal",
                          "--modality-consent", "audio_features", "--jurisdiction", "J"])
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stderr.decode()).get("error_code"), "consent_attester_required")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_3e_stream_turns_do_not_fire_prosody_without_consent(self):
        r = _run_cli(["-", "--mode", "generic", "--runner", "full",
                      "--stream-turns", "--no-seal"], input_text=PROSODY_NDJSON)
        self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
        events = _events(r.stdout.decode())
        self.assertNotIn("prosody", _cue_categories(events),
                         "prosody cues must not fire in the stream without audio_features consent")
        data = _final_package(r.stdout.decode())
        self.assertFalse(any(o.get("category") == "prosody" for o in data["observations"]))

    def test_3e_stream_turns_fire_prosody_with_consent(self):
        r = _run_cli(["-", "--mode", "generic", "--runner", "full",
                      "--stream-turns", "--no-seal",
                      "--modality-consent", "audio_features",
                      "--modality-attester", "officer-a", "--jurisdiction", "J"],
                     input_text=PROSODY_NDJSON)
        self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
        events = _events(r.stdout.decode())
        self.assertIn("prosody", _cue_categories(events),
                      "prosody cues must fire in the stream once audio_features consent is recorded")


class TestMalformedNdjsonStream(unittest.TestCase):
    """Task 4: a malformed NDJSON line must not kill the stream."""

    def test_malformed_line_skipped_stream_continues_and_seals(self):
        ndjson = (
            '{"role":"subject","text":"I think maybe I was around, you know."}\n'
            '{this is not json\n'
            '{"role":"officer","text":"Can you be specific?"}\n'
            '{"role":"subject","text":"I did not do it, I swear honestly never."}\n'
        )
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            r = _run_cli(["-", "--mode", "generic", "--stream-turns",
                          "--out-dir", str(out), "--basename", "pkg"],
                         input_text=ndjson)
            self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
            events = _events(r.stdout.decode())
            errs = [e for e in events if e.get("event") == "stream_line_error"]
            self.assertEqual(len(errs), 1)
            self.assertEqual(errs[0]["line"], 2)
            self.assertIn("error", errs[0])
            # Turns after the bad line still produced cues.
            self.assertTrue(any(e.get("event") == "new_cues" for e in events),
                            "later turns must still produce cues after a malformed line")
            end = [e for e in events if e.get("event") == "stream_end"]
            self.assertTrue(end and end[0].get("sealed"))
            self.assertEqual(end[0].get("stream_line_errors"), 1)
            pkg_path = out / "pkg.json"
            self.assertTrue(pkg_path.exists(), "final package must still be exported")
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            self.assertTrue(pkg.get("sealed"))
            self.assertTrue(verify_package_hash(pkg))
            self.assertTrue(len(pkg.get("observations") or []) > 0,
                            "accumulated turns must be present in the sealed package")


if __name__ == "__main__":
    unittest.main()
