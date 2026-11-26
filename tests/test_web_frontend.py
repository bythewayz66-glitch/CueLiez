"""Tests for the real web frontend (Track E).

The server is started in-process on an ephemeral port and exercised over
urllib. Every cue asserted here must come from the real pipeline run on the
submitted transcript — no canned cues.
"""

import json
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from cueliez.gates import verify_package_hash
from cueliez.web_frontend import WebFrontendServer, parse_ndjson_turns, run_pipeline

SAMPLE = json.loads(Path("docs/examples/sample_transcript.json").read_text(encoding="utf-8"))


def _post_json(url, payload, headers=None):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", **(headers or {})}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def _post_form(url, fields):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


class TestWebFrontend(unittest.TestCase):
    def setUp(self):
        self.srv = WebFrontendServer(host="127.0.0.1", port=0)
        self.srv.start()
        self.url = self.srv.url

    def tearDown(self):
        self.srv.stop()

    def test_home_page_loads_with_notice(self):
        with urllib.request.urlopen(self.url) as r:
            html = r.read().decode("utf-8")
        self.assertEqual(r.status, 200)
        self.assertIn("CueLiez Web Frontend", html)
        self.assertIn("Observation cues only, not findings", html)
        self.assertIn("transcript", html.lower())
        self.assertIn("/training", html)

    def test_real_transcript_post_produces_real_cues(self):
        status, body = _post_json(self.url + "api/run", {"transcript": SAMPLE})
        self.assertEqual(status, 200, body)
        self.assertTrue(body["ok"])
        self.assertGreaterEqual(body["cue_count"], 1)
        self.assertGreaterEqual(body["observation_count"], 1)
        model_ids = {
            (o.get("confidence") or {}).get("model_id")
            for o in body["observations"]
        }
        model_ids.discard(None)
        model_ids.discard("")
        self.assertTrue(model_ids, "observations must carry real model_ids")
        # Every cue's method must be a real observation model id.
        for cue in body["cues"]:
            self.assertIn(cue["method"], model_ids)
            self.assertIn("source_quotes", cue)
        # Same run through the direct helper agrees (no canned cues).
        direct = run_pipeline(SAMPLE)
        self.assertEqual(body["cue_count"], direct["cue_count"])
        self.assertEqual(
            [c["cue_id"] for c in body["cues"]],
            [c["cue_id"] for c in direct["cues"]],
        )

    def test_gated_mode_without_consent_fails_with_real_gate_error(self):
        status, body = _post_json(
            self.url + "api/run", {"transcript": SAMPLE, "mode": "interrogation"}
        )
        self.assertEqual(status, 403, body)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error_code"], "consent_required")
        self.assertIn("consent", body["error"].lower())

    def test_gated_mode_with_consent_and_training_runs(self):
        status, body = _post_json(
            self.url + "api/run",
            {
                "transcript": SAMPLE,
                "mode": "interrogation",
                "consent": True,
                "attested_by": "officer-a",
                "training_ack": True,
                "training_version": "v1",
            },
        )
        self.assertEqual(status, 200, body)
        self.assertGreaterEqual(body["cue_count"], 1)

    def test_seal_export_and_verify(self):
        status, body = _post_json(
            self.url + "api/run",
            {
                "transcript": SAMPLE,
                "mode": "interrogation",
                "consent": True,
                "attested_by": "officer-a",
                "training_ack": True,
                "training_version": "v1",
                "seal": True,
            },
        )
        self.assertEqual(status, 200, body)
        self.assertTrue(body["sealed"])
        pkg = body["package"]
        self.assertTrue(pkg.get("package_hash"))
        self.assertEqual(pkg.get("epistemic_status"), "observed_indicator")
        self.assertFalse(pkg.get("is_definitive_finding"))
        self.assertTrue(verify_package_hash(pkg))

        # Export JSON downloads the sealed package and it still verifies.
        with urllib.request.urlopen(self.url + "api/export?format=json") as r:
            exported = json.loads(r.read().decode("utf-8"))
        self.assertEqual(exported["package_hash"], pkg["package_hash"])
        self.assertTrue(verify_package_hash(exported))

        # Export Markdown and HTML render the real cues.
        with urllib.request.urlopen(self.url + "api/export?format=md") as r:
            md = r.read().decode("utf-8")
        self.assertIn(pkg["package_hash"], md)
        with urllib.request.urlopen(self.url + "api/export?format=html") as r:
            html = r.read().decode("utf-8")
        self.assertIn(pkg["package_hash"], html)

        # Verify endpoint returns hash_ok true for the good package.
        status, ver = _post_json(self.url + "api/verify", {"package": exported})
        self.assertEqual(status, 200, ver)
        self.assertTrue(ver["hash_ok"])
        self.assertTrue(ver["ok"])

        # Tampered package fails verification.
        bad = dict(exported)
        bad["observations"] = []
        status, ver = _post_json(self.url + "api/verify", {"package": bad})
        self.assertEqual(status, 200, ver)
        self.assertFalse(ver["hash_ok"])

    def test_separate_seal_endpoint_seals_last_run(self):
        status, body = _post_json(
            self.url + "api/run",
            {
                "transcript": SAMPLE,
                "mode": "interrogation",
                "consent": True,
                "attested_by": "officer-a",
                "training_ack": True,
                "training_version": "v1",
            },
        )
        self.assertEqual(status, 200, body)
        self.assertFalse(body["sealed"])
        status, sealed = _post_json(self.url + "api/seal", {})
        self.assertEqual(status, 200, sealed)
        self.assertTrue(sealed["sealed"])
        self.assertTrue(verify_package_hash(sealed["package"]))

    def test_officer_notes_attached_before_seal(self):
        status, body = _post_json(self.url + "api/run", {"transcript": SAMPLE})
        self.assertEqual(status, 200, body)
        cue_id = body["cues"][0]["cue_id"]
        status, noted = _post_json(
            self.url + "api/notes",
            {"officer_cue_notes": [{"cue_id": cue_id, "action": "noted", "note": "checked", "officer_id": "officer-a"}]},
        )
        self.assertEqual(status, 200, noted)
        self.assertEqual(noted["officer_cue_notes"][0]["cue_id"], cue_id)
        status, sealed = _post_json(self.url + "api/seal", {})
        self.assertEqual(status, 200, sealed)
        self.assertEqual(sealed["package"]["officer_cue_notes"][0]["cue_id"], cue_id)

    def test_stream_ndjson_reports_malformed_lines_and_returns_new_cues(self):
        ndjson = (
            '{"role": "subject", "text": "I think maybe I was around the area."}\n'
            "not json at all\n"
            '{"role": "subject", "text": "I don\'t really remember exactly."}\n'
            "\n"
            '{"role": "officer", "text": "What specific location?"}\n'
        )
        req = urllib.request.Request(
            self.url + "api/stream",
            data=ndjson.encode("utf-8"),
            headers={"Content-Type": "application/x-ndjson"},
            method="POST",
        )
        with urllib.request.urlopen(req) as r:
            body = json.loads(r.read().decode("utf-8"))
        self.assertTrue(body["ok"])
        self.assertEqual(body["turn_count"], 3)
        self.assertEqual(body["malformed_lines"], 1)
        self.assertEqual(len(body["errors"]), 1)
        self.assertEqual(body["errors"][0]["line"], 2)
        self.assertGreaterEqual(body["new_cue_count"], 1)
        # Second batch on the same session with no new turns returns no new cues.
        req = urllib.request.Request(
            self.url + "api/stream",
            data=json.dumps({"turns": [], "session_id": body["session_id"]}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as r:
            again = json.loads(r.read().decode("utf-8"))
        self.assertEqual(again["new_cue_count"], 0)
        self.assertEqual(again["turn_count"], 3)

    def test_parse_ndjson_helper_per_line_errors(self):
        turns, errors = parse_ndjson_turns('{"role":"subject","text":"hi"}\nbroken\n{"role":"subject","text":"yo"}\n')
        self.assertEqual(len(turns), 2)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["line"], 2)

    def test_training_page_lists_real_modules(self):
        from cueliez.compliance.training import get_training_bundle

        with urllib.request.urlopen(self.url + "training") as r:
            html = r.read().decode("utf-8")
        for module in get_training_bundle():
            self.assertIn(module.title, html)
            self.assertIn(module.id, html)
        with urllib.request.urlopen(self.url + "api/training") as r:
            data = json.loads(r.read().decode("utf-8"))
        self.assertEqual(len(data["modules"]), len(get_training_bundle()))

    def test_malicious_transcript_is_escaped_in_html(self):
        evil = [
            {"role": "officer", "text": "Where were you?"},
            {"role": "subject", "text": "I think maybe <script>alert(1)</script> around the area, you know."},
        ]
        status, html = _post_form(
            self.url + "run",
            {
                "transcript": json.dumps(evil),
                "mode": "generic",
            },
        )
        self.assertEqual(status, 200, html[:500])
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_token_auth_when_configured(self):
        with WebFrontendServer(host="127.0.0.1", port=0, token="secret-token") as srv:
            try:
                urllib.request.urlopen(srv.url)
                self.fail("expected 401")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 401)
            req = urllib.request.Request(srv.url, headers={"Authorization": "Bearer secret-token"})
            with urllib.request.urlopen(req) as r:
                self.assertEqual(r.status, 200)

    def test_origin_rejected_when_not_allowed(self):
        req = urllib.request.Request(self.url, headers={"Origin": "https://evil.example"})
        try:
            urllib.request.urlopen(req)
            self.fail("expected 403")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)


if __name__ == "__main__":
    unittest.main()
