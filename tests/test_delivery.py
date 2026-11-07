import json
import tempfile
import unittest
import wave
from pathlib import Path

from cueliez.delivery import AudioCueRenderer, OnscreenCueRenderer, cues_from_observations, generate_tone_wav
from cueliez.observations import default_runner


SAMPLE_OBS = [
    {"label": "hedging_language_present", "confidence": {"score": 0.72, "model_id": "m/v1"},
     "category": "linguistic", "method": "m/v1", "cue": "Ask for specific details.", "turn_index": 1,
     "evidence": {"count": 3}},
    {"label": "possible_statement_conflict", "confidence": {"score": 0.65, "model_id": "m/v1"},
     "category": "consistency", "method": "m/v1", "cue": "Ask the subject to reconcile accounts.", "turn_index": 3,
     "evidence": {"turn_a": 1, "turn_b": 3}},
    {"label": "low_signal", "confidence": {"score": 0.2, "model_id": "m/v1"},
     "category": "linguistic", "method": "m/v1", "cue": "Minor note.", "turn_index": 0},
]


class TestCueEvents(unittest.TestCase):
    def test_cues_from_observations(self):
        cues = cues_from_observations(SAMPLE_OBS)
        self.assertEqual(len(cues), 3)
        # consistency/high-score sorting should put conflict high
        priorities = [c.priority for c in cues]
        self.assertIn(cues[0].label, ("possible_statement_conflict", "hedging_language_present"))
        self.assertTrue(all(c.non_verdict_notice for c in cues))
        self.assertTrue(all("observation cue" in c.audio_script.lower() or "not a finding" in c.audio_script.lower() for c in cues))

    def test_min_score_and_max(self):
        cues = cues_from_observations(SAMPLE_OBS, min_score=0.6)
        self.assertTrue(all(c.score >= 0.6 for c in cues))
        cues = cues_from_observations(SAMPLE_OBS, max_cues=1)
        self.assertEqual(len(cues), 1)

    def test_dedup(self):
        dup = [SAMPLE_OBS[0], dict(SAMPLE_OBS[0])]
        self.assertEqual(len(cues_from_observations(dup)), 1)

    def test_to_dict(self):
        d = cues_from_observations(SAMPLE_OBS)[0].to_dict()
        for k in ("cue_id", "priority", "onscreen_text", "audio_script", "non_verdict_notice"):
            self.assertIn(k, d)


class TestOnscreenRenderer(unittest.TestCase):
    def test_render_text(self):
        cues = cues_from_observations(SAMPLE_OBS)
        text = OnscreenCueRenderer().render_text(cues, header="Session")
        self.assertIn("Session", text)
        self.assertIn("Observation cues", text)
        self.assertIn("not findings", text.lower())
        self.assertIn("not determinations", text.lower())

    def test_render_text_empty(self):
        text = OnscreenCueRenderer().render_text([])
        self.assertIn("No observation cues", text)

    def test_render_panel(self):
        panel = OnscreenCueRenderer(show_evidence=True).render_panel(SAMPLE_OBS)
        self.assertEqual(panel["type"], "cueliez_onscreen_cues")
        self.assertEqual(panel["cue_count"], 3)
        self.assertIn("cues", panel)
        self.assertIn("text", panel)
        self.assertIn("not findings", panel["notice"].lower())

    def test_render_html(self):
        html = OnscreenCueRenderer().render_html(cues_from_observations(SAMPLE_OBS))
        self.assertIn("<section", html)
        self.assertIn("not findings", html.lower())
        self.assertIn("Ask for specific details", html)
        self.assertNotIn("lie detector", html.lower())

    def test_no_verdict_language_in_output(self):
        panel = OnscreenCueRenderer().render_panel(SAMPLE_OBS)
        blob = json.dumps(panel).lower()
        for bad in ("lie detector", "detects lies", "subject is lying", "confirms lying"):
            self.assertNotIn(bad, blob)


class TestAudioRenderer(unittest.TestCase):
    def test_generate_tone_wav(self):
        with tempfile.TemporaryDirectory() as td:
            for p in ("low", "medium", "high", "critical"):
                path = generate_tone_wav(Path(td) / f"{p}.wav", priority=p)
                self.assertTrue(Path(path).exists())
                with wave.open(path, "rb") as wf:
                    self.assertEqual(wf.getnchannels(), 1)
                    self.assertEqual(wf.getsampwidth(), 2)
                    self.assertEqual(wf.getframerate(), 22050)
                    self.assertGreater(wf.getnframes(), 100)

    def test_render_assets(self):
        cues = cues_from_observations(SAMPLE_OBS)
        with tempfile.TemporaryDirectory() as td:
            r = AudioCueRenderer(output_dir=td, allow_playback=False)
            manifest = r.render_assets(cues)
            self.assertEqual(manifest["type"], "cueliez_audio_cues")
            self.assertEqual(manifest["cue_count"], len(cues))
            self.assertTrue((Path(td) / "manifest.json").exists())
            for a in manifest["assets"]:
                self.assertTrue(Path(a["tone_wav"]).exists())
                self.assertTrue(Path(a["script_text"]).exists())
                self.assertIn("not a finding", a["audio_script"].lower())
            loaded = json.loads((Path(td) / "manifest.json").read_text())
            self.assertIn("not findings", loaded["notice"].lower())

    def test_render_panel(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = AudioCueRenderer(output_dir=td).render_panel(SAMPLE_OBS)
            self.assertEqual(manifest["cue_count"], 3)

    def test_playback_disabled(self):
        with tempfile.TemporaryDirectory() as td:
            path = generate_tone_wav(Path(td) / "t.wav")
            res = AudioCueRenderer(allow_playback=False).play_tone(path)
            self.assertFalse(res["played"])
            self.assertEqual(res["reason"], "playback_disabled")


class TestDeliveryIntegration(unittest.TestCase):
    def test_from_runner_observations(self):
        t = [
            {"role": "subject", "text": "I think maybe I was around doing stuff, you know.", "response_latency_ms": 4500},
            {"role": "subject", "text": "I did not do it, I swear honestly never."},
            {"role": "subject", "text": "Why would you ask that? I already told you."},
        ]
        obs = default_runner().run(t)
        onscreen = OnscreenCueRenderer().render_panel(obs)
        self.assertGreaterEqual(onscreen["cue_count"], 1)
        with tempfile.TemporaryDirectory() as td:
            audio = AudioCueRenderer(output_dir=td).render_panel(obs)
            self.assertEqual(audio["cue_count"], onscreen["cue_count"])


if __name__ == "__main__":
    unittest.main()
