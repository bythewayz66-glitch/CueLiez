import base64
import hashlib
import json
import os
import re
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from cueliez.delivery import LiveDashboardServer, OnscreenCueRenderer, cues_from_observations

from tests import js_dom_harness as H

REPO = Path(__file__).resolve().parents[1]
REVIEW_HTML = REPO / "docs" / "site" / "review.html"

MARKUP_PAYLOADS = [
    "<script>window.__pwned=1</script>",
    '"><img src=x onerror="window.__pwned=1">',
    "</script><script>window.__pwned=1</script>",
    "' onmouseover='window.__pwned=1' x='",
    '" onfocus="window.__pwned=1" autofocus="',
    "javascript:window.__pwned=1",
    "<svg/onload=window.__pwned=1>",
    '<a href="javascript:window.__pwned=1">x</a>',
    "&lt;script&gt;window.__pwned=1&lt;/script&gt;",
    "<!--",
    "＜script＞window.__pwned=1＜/script＞",
    "<iframe srcdoc='<script>parent.__pwned=1</script>'>",
    "<style>*{display:none}</style>",
    "<math><mtext><table><mglyph><style><img src=x onerror=window.__pwned=1>",
]

CONTROL_PAYLOADS = {
    "ansi_osc": "a\x1b]0;pwned\x07b",
    "ansi_csi": "a\x1b[31mred\x1b[0mb",
    "bidi_override": "a\u202eb",
    "bidi_isolate": "a\u2066b\u2069",
    "line_sep": "a\u2028b\u2029c",
    "nul": "a\x00b",
    "c1": "a\x9bb",
}

DASHBOARD_TAGS = {"div", "span", "p"}
REVIEW_TAGS = {"section", "h2", "div", "p", "strong", "ul", "li", "table", "thead", "tbody", "tr", "th", "td", "code", "span", "br"}
OFFICER_TAGS = {
    "html", "head", "meta", "title", "style", "body", "header", "h1", "h2", "p", "div", "button", "main",
    "pre", "script", "article", "span", "textarea", "strong", "code", "section", "table", "thead", "tbody",
    "tr", "th", "td",
}

BIDI_AND_CONTROL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u2028\u2029\u202a-\u202e\u2066-\u2069\u200e\u200f\u061c]")


def _need_node(testcase: unittest.TestCase) -> None:
    if H.NODE is None:
        if os.environ.get("CI"):
            testcase.fail("node is required in CI for client-side rendering tests")
        testcase.skipTest("node not installed; client-side rendering tests need it")


def _served_dashboard_html() -> str:
    with LiveDashboardServer(host="127.0.0.1", port=0) as srv:
        with urllib.request.urlopen(srv.url) as r:
            return r.read().decode("utf-8")


def _hostile_obs(payload: str, i: int = 0) -> dict:
    return {
        "label": payload, "category": payload, "method": payload, "cue": payload, "cue_id": payload,
        "turn_index": 1, "priority": payload,
        "confidence": {"score": 0.9, "model_id": "m"},
        "evidence": {
            "quotes": [{"text": payload, "role": payload, "turn_index": 1}],
            "topic_key": payload, "categories": [payload],
        },
    }


class OfficerHtmlEscapingTests(unittest.TestCase):
    def test_render_officer_html_has_no_injected_markup(self):
        for payload in MARKUP_PAYLOADS:
            with self.subTest(payload=payload):
                h = OnscreenCueRenderer().render_officer_html([_hostile_obs(payload)], title=payload)
                col = H.parse_markup(h)
                self.assertEqual(H.markup_violations(col.tags, OFFICER_TAGS), [])
                self.assertEqual(sum(1 for t, _ in col.tags if t == "script"), 2)
                self.assertEqual(sum(1 for t, _ in col.tags if t == "style"), 1)

    def test_render_officer_html_transcript_fallback_quotes(self):
        for payload in MARKUP_PAYLOADS:
            with self.subTest(payload=payload):
                obs = [{"label": "x", "category": "linguistic", "method": "m", "cue": "c", "turn_index": 0,
                        "confidence": {"score": 0.9, "model_id": "m"}}]
                h = OnscreenCueRenderer().render_officer_html(obs, transcript=[{"role": payload, "text": payload}])
                col = H.parse_markup(h)
                self.assertEqual(H.markup_violations(col.tags, OFFICER_TAGS), [])
                self.assertIn(payload, "".join(col.text))

    def test_render_officer_html_json_block_round_trips(self):
        for payload in MARKUP_PAYLOADS + list(CONTROL_PAYLOADS.values()):
            with self.subTest(payload=payload):
                obs = [_hostile_obs(payload)]
                h = OnscreenCueRenderer().render_officer_html(obs)
                m = re.search(r'<script id="cue-data" type="application/json">(.*?)</script', h, re.S)
                self.assertIsNotNone(m)
                body = m.group(1)
                self.assertNotIn("<", body)
                self.assertNotIn("\u2028", body)
                self.assertNotIn("\u2029", body)
                expected = [c.to_dict() for c in cues_from_observations(obs)]
                self.assertEqual(json.loads(body), json.loads(json.dumps(expected)))

    def test_render_html_has_no_injected_markup(self):
        for payload in MARKUP_PAYLOADS:
            with self.subTest(payload=payload):
                cues = cues_from_observations([_hostile_obs(payload)])
                h = OnscreenCueRenderer().render_html(cues, title=payload)
                col = H.parse_markup(h)
                self.assertEqual(H.markup_violations(col.tags, {"section", "h2", "p", "table", "thead", "tbody", "tr", "th", "td", "div", "strong", "code"}), [])
                self.assertIn(payload, "".join(col.text))

    def test_control_and_bidi_characters_are_not_emitted_raw(self):
        for name, payload in CONTROL_PAYLOADS.items():
            with self.subTest(payload=name):
                obs = [_hostile_obs(payload)]
                cues = cues_from_observations(obs)
                for out in (
                    OnscreenCueRenderer().render_html(cues),
                    OnscreenCueRenderer().render_officer_html(obs),
                ):
                    visible = "".join(H.parse_markup(re.sub(r"<script.*?</script>", "", out, flags=re.S)).text)
                    self.assertIsNone(BIDI_AND_CONTROL.search(visible.replace("\n", "")))
                self.assertIsNone(BIDI_AND_CONTROL.search(OnscreenCueRenderer().render_html(cues).replace("\n", "")))


class TerminalTextEscapingTests(unittest.TestCase):
    def test_render_text_strips_terminal_control_sequences(self):
        for name, payload in CONTROL_PAYLOADS.items():
            with self.subTest(payload=name):
                obs = [_hostile_obs(payload)]
                cues = cues_from_observations(obs)
                text = OnscreenCueRenderer(show_evidence=True).render_text(cues, header=payload)
                self.assertIsNone(BIDI_AND_CONTROL.search(text.replace("\n", "")))

    def test_render_text_with_colour_only_emits_own_sequences(self):
        cues = cues_from_observations([_hostile_obs(CONTROL_PAYLOADS["ansi_osc"])])
        text = OnscreenCueRenderer(use_color=True).render_text(cues)
        self.assertNotIn("\x1b]", text)
        self.assertNotIn("\x07", text)


class DashboardClientTests(unittest.TestCase):
    def setUp(self):
        _need_node(self)
        self.tmp = Path(tempfile.mkdtemp())
        scripts = H.extract_inline_scripts(_served_dashboard_html())
        self.assertEqual(len(scripts), 1)
        self.script = scripts[0]

    def _run(self, cues):
        return H.run_script(self.script, ids=["status", "cues"], fetch_json={"cues": cues}, tmp_dir=self.tmp)

    def test_hostile_cue_fields_do_not_become_markup(self):
        cues = []
        for i, p in enumerate(MARKUP_PAYLOADS):
            cues.append({
                "cue_id": f"{p}#id{i}", "message": f"{p}#msg{i}", "priority": p, "category": f"{p}#cat{i}",
                "turn_index": f"{p}#turn{i}", "score": 0.5,
                "source_quotes": [{"quote": f"{p}#quote{i}", "turn_index": f"{p}#qturn{i}"}, {"text": f"{p}#text{i}"}],
            })
        res = self._run(cues)
        self.assertEqual(res["errors"], [])
        violations, text = H.analyse(res, DASHBOARD_TAGS)
        self.assertEqual(violations, [])
        for i, p in enumerate(MARKUP_PAYLOADS):
            for field in ("id", "msg", "cat", "turn", "quote", "qturn", "text"):
                self.assertIn(f"{p}#{field}{i}", text, f"{field} of payload {i} not displayed verbatim")

    def test_quote_fallback_to_text_is_displayed(self):
        res = self._run([{"cue_id": "c1", "message": "m", "score": 0.5, "source_quotes": [{"text": "the quoted words", "turn_index": 3}]}])
        _, text = H.analyse(res, DASHBOARD_TAGS)
        self.assertIn("the quoted words", text)
        self.assertIn("(T3)", text)

    def test_control_characters_are_made_visible_not_raw(self):
        cues = [{"cue_id": f"c{i}", "message": v, "score": 0.5, "source_quotes": [{"quote": v}]} for i, v in enumerate(CONTROL_PAYLOADS.values())]
        res = self._run(cues)
        _, text = H.analyse(res, DASHBOARD_TAGS)
        self.assertIsNone(BIDI_AND_CONTROL.search(text.replace("\n", "")))
        self.assertIn("U+202E", text)
        self.assertIn("U+001B", text)

    def test_malformed_cue_values_do_not_break_the_page(self):
        cues = [
            {"cue_id": "a", "message": "first", "score": "not-a-number", "priority": 5},
            {"cue_id": "b", "message": {"k": "<img src=x onerror=window.__pwned=1>"}, "source_quotes": [None, "str", {"quote": None}]},
            {"cue_id": "c", "message": "third", "turn_index": {"x": 1}, "score": None},
        ]
        res = self._run(cues)
        self.assertEqual(res["errors"], [])
        violations, text = H.analyse(res, DASHBOARD_TAGS)
        self.assertEqual(violations, [])
        status = H.tree_text(res["roots"]["status"])
        self.assertTrue(status.startswith("Cues: 3"), status)
        self.assertIn("first", text)
        self.assertIn("third", text)

    def test_empty_state_unchanged(self):
        res = self._run([])
        _, text = H.analyse(res, DASHBOARD_TAGS)
        self.assertIn("No observation cues at current thresholds.", text)

    def test_normal_cue_display_unchanged(self):
        res = self._run([{"cue_id": "cue-t1-x", "message": "Ask for specific details", "priority": "high", "score": 0.5, "category": "linguistic", "turn_index": 1,
                          "source_quotes": [{"quote": "I think so", "turn_index": 1}]}])
        _, text = H.analyse(res, DASHBOARD_TAGS)
        for expected in ("HIGH", "Turn 1", "Ask for specific details", "score=0.50", "linguistic", "cue-t1-x", '"I think so" (T1)'):
            self.assertIn(expected, text)


class ReviewPageClientTests(unittest.TestCase):
    def setUp(self):
        _need_node(self)
        self.tmp = Path(tempfile.mkdtemp())
        scripts = H.extract_inline_scripts(REVIEW_HTML.read_text(encoding="utf-8"))
        self.assertEqual(len(scripts), 1)
        self.script = scripts[0]

    def _render(self, pkg):
        return H.run_script(
            self.script, ids=["input", "render", "error", "out", "drop"],
            values={"input": json.dumps(pkg)}, steps=[{"id": "render", "call": "onclick"}], tmp_dir=self.tmp,
        )

    def _assert_safe(self, res, expected_texts):
        self.assertEqual(res["errors"], [])
        self.assertEqual(H.tree_text(res["roots"]["error"]), "")
        violations, text = H.analyse(res, REVIEW_TAGS)
        self.assertEqual(violations, [])
        for t in expected_texts:
            self.assertIn(t, text)

    def test_package_with_cues_and_notes_is_inert(self):
        cues, notes, expected = [], [], []
        for i, p in enumerate(MARKUP_PAYLOADS):
            cues.append({"priority": "high", "turn_index": f"{p}#turn{i}", "cue_id": f"{p}#id{i}", "label": f"{p}#label{i}", "score": 0.5, "message": f"{p}#msg{i}"})
            notes.append({"cue_id": f"{p}#nid{i}", "action": f"{p}#act{i}", "note": f"{p}#note{i}", "officer_id": f"{p}#off{i}"})
            expected += [f"{p}#{f}{i}" for f in ("turn", "id", "label", "msg", "nid", "act", "note")]
        p0 = MARKUP_PAYLOADS[1]
        pkg = {
            "cues": cues, "officer_cue_notes": notes, "observations": [{}],
            "disclaimer": p0 + "#disc", "epistemic_status": p0 + "#epi", "is_definitive_finding": p0 + "#def",
            "product": p0 + "#prod", "product_version": p0 + "#pv", "schema_version": p0 + "#sv",
            "package_hash": p0 + "#hash", "sealed_at": p0 + "#sealed",
            "gate_state": {"mode": p0 + "#mode", "intended_uses": [p0]},
            "firewall": {"consent_rechecked": p0 + "#cons", "training_rechecked": p0 + "#train"},
        }
        expected += [p0 + s for s in ("#disc", "#epi", "#def", "#prod", "#pv", "#sv", "#hash", "#sealed", "#mode", "#cons", "#train")]
        self._assert_safe(self._render(pkg), expected)

    def test_observation_derived_rows_are_inert(self):
        obs, expected = [], []
        for i, p in enumerate(MARKUP_PAYLOADS):
            obs.append({"priority": "high", "turn_index": f"{p}#turn{i}", "cue_id": f"{p}#id{i}", "label": f"{p}#label{i}",
                        "confidence": {"score": f"{p}#score{i}"}, "cue": f"{p}#cue{i}"})
            expected += [f"{p}#{f}{i}" for f in ("turn", "id", "label", "cue")]
        self._assert_safe(self._render({"observations": obs}), expected)

    def test_annotation_mode_is_inert(self):
        p = MARKUP_PAYLOADS[0]
        self._assert_safe(self._render({"annotations": {"mode": p + "#m"}, "observations": []}), [p + "#m"])

    def test_normal_package_display_unchanged(self):
        pkg = {
            "epistemic_status": "observed_indicator", "is_definitive_finding": False, "product": "CueLiez",
            "disclaimer": "Observation cues only.", "package_hash": "abc123", "sealed_at": 1700000000,
            "observations": [{"priority": "medium", "turn_index": 2, "cue_id": "cue-t2", "label": "hedging", "confidence": {"score": 0.61}, "cue": "Ask for specific details"}],
            "officer_cue_notes": [{"cue_id": "cue-t2", "action": "noted", "note": "Context recorded."}],
        }
        res = self._render(pkg)
        self._assert_safe(res, ["observed_indicator", "Observation cues only.", "abc123", "cue-t2", "hedging", "0.61", "Ask for specific details", "Officer Notes (Human)", "[noted]: Context recorded."])

    def test_unparseable_input_shows_error_text_only(self):
        res = H.run_script(self.script, ids=["input", "render", "error", "out", "drop"], values={"input": "<img src=x onerror=window.__pwned=1>"},
                           steps=[{"id": "render", "call": "onclick"}], tmp_dir=self.tmp)
        violations, _ = H.analyse(res, REVIEW_TAGS)
        self.assertEqual(violations, [])
        self.assertTrue(H.tree_text(res["roots"]["error"]).startswith("Could not parse JSON"))


FORBIDDEN_SINKS = re.compile(r"\.innerHTML|\.outerHTML|insertAdjacentHTML|document\.write|\beval\s*\(|new\s+Function|\.srcdoc|setAttribute\(\s*['\"]on", re.I)


class ClientSinkGuardTests(unittest.TestCase):
    def test_dashboard_script_uses_no_raw_html_sinks(self):
        for s in H.extract_inline_scripts(_served_dashboard_html()):
            self.assertIsNone(FORBIDDEN_SINKS.search(s))

    def test_review_script_uses_no_raw_html_sinks(self):
        for s in H.extract_inline_scripts(REVIEW_HTML.read_text(encoding="utf-8")):
            self.assertIsNone(FORBIDDEN_SINKS.search(s))

    def test_officer_html_script_uses_no_raw_html_sinks(self):
        h = OnscreenCueRenderer().render_officer_html([_hostile_obs("x")])
        for s in H.extract_inline_scripts(h):
            self.assertIsNone(FORBIDDEN_SINKS.search(s))


def _csp_hash(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode() + "'"


def _csp_directives(policy: str) -> dict:
    out = {}
    for part in policy.split(";"):
        bits = part.strip().split()
        if bits:
            out[bits[0]] = bits[1:]
    return out


def _inline_style_blocks(html_text: str):
    return [m.group(1) for m in re.finditer(r"<style[^>]*>(.*?)</style>", html_text, re.S | re.I)]


class DashboardHeadersAndOriginTests(unittest.TestCase):
    def _get(self, url, headers=None):
        req = urllib.request.Request(url, headers=headers or {})
        return urllib.request.urlopen(req)

    def test_csp_header_pins_inline_script_and_style(self):
        with LiveDashboardServer(host="127.0.0.1", port=0) as srv:
            with self._get(srv.url) as r:
                body = r.read().decode("utf-8")
                policy = r.headers.get("Content-Security-Policy")
        self.assertIsNotNone(policy)
        d = _csp_directives(policy)
        self.assertEqual(d["default-src"], ["'none'"])
        scripts = H.extract_inline_scripts(body)
        self.assertEqual(d["script-src"], [_csp_hash(s) for s in scripts])
        self.assertEqual(d["style-src"], [_csp_hash(s) for s in _inline_style_blocks(body)])
        self.assertEqual(d["connect-src"], ["'self'"])
        self.assertEqual(d["base-uri"], ["'none'"])
        self.assertEqual(d["form-action"], ["'none'"])
        self.assertEqual(d["frame-ancestors"], ["'none'"])
        self.assertNotIn("'unsafe-inline'", policy)
        self.assertNotIn("'unsafe-eval'", policy)

    def test_hardening_headers_on_page_and_cues(self):
        with LiveDashboardServer(host="127.0.0.1", port=0) as srv:
            for path in ("", "cues"):
                with self._get(srv.url + path) as r:
                    self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff", path)
                    self.assertEqual(r.headers.get("Cache-Control"), "no-store", path)
                    self.assertEqual(r.headers.get("Referrer-Policy"), "no-referrer", path)

    def test_hostile_cues_round_trip_as_json_only(self):
        payloads = MARKUP_PAYLOADS + list(CONTROL_PAYLOADS.values())
        cues = [{"cue_id": f"c{i}", "message": p, "priority": p, "source_quotes": [{"quote": p, "text": p}]} for i, p in enumerate(payloads)]
        with LiveDashboardServer(host="127.0.0.1", port=0) as srv:
            req = urllib.request.Request(srv.url + "cues", data=json.dumps({"cues": cues}).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as r:
                self.assertTrue(json.loads(r.read())["ok"])
            with self._get(srv.url + "cues") as r:
                self.assertEqual(r.headers.get_content_type(), "application/json")
                self.assertEqual(json.loads(r.read())["cues"], cues)
            with self._get(srv.url) as r:
                page = r.read().decode("utf-8")
            for p in MARKUP_PAYLOADS:
                self.assertNotIn(p, page)

    def test_origin_check_is_exact_host_match(self):
        bad = [
            "http://127.0.0.1.evil.example", "http://localhost.evil.example", "https://localhost.evil.example:8443",
            "http://127.0.0.10", "http://127.0.0.1@evil.example", "null", "http://evil.example", "file://",
        ]
        good = ["http://127.0.0.1", "http://127.0.0.1:8765", "http://localhost:3000", "https://localhost", "http://[::1]:8080"]
        with LiveDashboardServer(host="127.0.0.1", port=0) as srv:
            for origin in bad:
                with self.subTest(origin=origin):
                    with self.assertRaises(urllib.error.HTTPError) as cm:
                        self._get(srv.url, {"Origin": origin})
                    self.assertEqual(cm.exception.code, 403)
            for origin in good:
                with self.subTest(origin=origin):
                    with self._get(srv.url, {"Origin": origin}) as r:
                        self.assertEqual(r.status, 200)

    def test_cross_origin_post_cannot_replace_cues(self):
        with LiveDashboardServer(host="127.0.0.1", port=0) as srv:
            srv.push_cues([{"cue_id": "keep", "message": "kept"}])
            req = urllib.request.Request(
                srv.url + "cues", data=json.dumps({"cues": [{"cue_id": "x", "message": "<script>window.__pwned=1</script>"}]}).encode(),
                headers={"Content-Type": "text/plain", "Origin": "http://127.0.0.1.evil.example"},
            )
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(req)
            self.assertEqual(cm.exception.code, 403)
            with self._get(srv.url + "cues") as r:
                self.assertEqual(json.loads(r.read())["cues"][0]["cue_id"], "keep")


class ReviewAndOfficerCspTests(unittest.TestCase):
    def _assert_meta_csp(self, html_text):
        m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', html_text)
        self.assertIsNotNone(m, "meta CSP missing")
        d = _csp_directives(m.group(1))
        self.assertEqual(d["default-src"], ["'none'"])
        self.assertEqual(d["script-src"], [_csp_hash(s) for s in H.extract_inline_scripts(html_text)])
        self.assertEqual(d["style-src"], [_csp_hash(s) for s in _inline_style_blocks(html_text)])
        self.assertEqual(d["base-uri"], ["'none'"])
        self.assertEqual(d["form-action"], ["'none'"])
        self.assertNotIn("'unsafe-inline'", m.group(1))

    def test_review_page_has_matching_csp(self):
        self._assert_meta_csp(REVIEW_HTML.read_text(encoding="utf-8"))

    def test_officer_html_has_matching_csp(self):
        self._assert_meta_csp(OnscreenCueRenderer().render_officer_html([_hostile_obs("x")]))


if __name__ == "__main__":
    unittest.main()
