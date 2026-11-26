"""Live AV surface tests (Phase 10, Track D).

Covers: consent gates blocking mic/camera start (zero source opens),
mode refusal, kill switch, per-modality stop, sealed-package modality
timeline + hash, timing cues behind their own consent + baseline,
video cues at the lowest priority with no frames stored, unconfirmed
speakers never sourcing cues, raw-media rejection, chunk dedup/gap,
cloud transcription fail-closed, and real face matching end-to-end
with real public-domain portraits (skipped when the ``face`` extra is
not installed).

Face fixtures: tests/fixtures/face/*.jpg -- real public-domain White
House portraits (Obama x3, Biden x2). The observer is Track B's
(cueliez.observations.face_recognition); these tests cover only the
live-surface side (gating, enrollment/matching through LiveSession,
template deletion on stop).
"""

import base64
import json
import struct
import unittest
import urllib.error
import urllib.request
import zlib
from pathlib import Path

import pytest

from cueliez.gates import GateError, SessionGateState, record_modality_consent, verify_package_hash
from cueliez.live_av import (
    BrowserSttAdapter,
    CloudSttAdapter,
    CloudSttNotConfigured,
    FaceRecError,
    LiveAvServer,
    LiveSession,
    SttNotAvailable,
    VideoWindow,
    available_face_rec_backends,
    format_timing_cue,
    format_video_cue,
    live_modality_allowed,
    record_live_modality_consent,
    require_live_modality,
    vosk_adapter,
)
from cueliez.observations.audio_stream import LiveAudioTimingHook
from cueliez.observations.audio_path import observe_live_audio_timing
from cueliez.observations.visual import GazePatternObserver

FACE_AVAILABLE = bool(available_face_rec_backends())
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "face"


class FakeCaptureSource:
    """Counts opens; never touches hardware."""

    def __init__(self):
        self.open_count = 0
        self.close_count = 0

    def open(self):
        self.open_count += 1

    def close(self):
        self.close_count += 1


def _state_with(*modalities, mode="generic"):
    s = SessionGateState(mode=mode)
    for m in modalities:
        record_live_modality_consent(s, m, attested_by="officer/a", jurisdiction="CO", jurisdiction_approved=True)
    return s


def _subject_turn(text, *, latency_ms=None, duration_ms=3000):
    t = {"role": "subject", "text": text, "duration_ms": duration_ms}
    if latency_ms is not None:
        t["response_latency_ms"] = latency_ms
    return t


def _white_png_bytes(size=120):
    """A solid-white PNG with no face (stdlib only)."""
    raw = b"".join(b"\x00" + b"\xff\xff\xff" * size for _ in range(size))
    compressed = zlib.compress(raw)
    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


class TestLiveConsentGates(unittest.TestCase):
    def test_mic_start_refused_without_audio_capture_consent(self):
        s = _state_with("audio_features")  # timing consent does NOT enable capture
        src = FakeCaptureSource()
        ls = LiveSession(s, baseline_window_s=0)
        with self.assertRaises(GateError) as ctx:
            ls.start_audio(capture_source=src)
        self.assertEqual(ctx.exception.code, "modality_consent_required")
        self.assertEqual(src.open_count, 0, "capture source must never open on refusal")

    def test_camera_start_refused_without_camera_consent(self):
        s = _state_with("audio_capture")
        src = FakeCaptureSource()
        ls = LiveSession(s, baseline_window_s=0)
        with self.assertRaises(GateError) as ctx:
            ls.start_video(capture_source=src)
        self.assertEqual(ctx.exception.code, "modality_consent_required")
        self.assertEqual(src.open_count, 0)

    def test_face_start_refused_without_face_recognition_consent(self):
        s = _state_with("audio_capture")
        ls = LiveSession(s, baseline_window_s=0)
        with self.assertRaises(GateError) as ctx:
            ls.enable_face_recognition()
        self.assertEqual(ctx.exception.code, "modality_consent_required")

    def test_mode_refusal(self):
        for mode in ("therapy", "clinical", "government"):
            s = _state_with("audio_capture", "camera", mode=mode)
            src = FakeCaptureSource()
            ls = LiveSession(s, baseline_window_s=0)
            with self.assertRaises(GateError) as ctx:
                ls.start_audio(capture_source=src)
            self.assertEqual(ctx.exception.code, "live_mode_refused")
            self.assertEqual(src.open_count, 0)

    def test_per_record_jurisdiction_approval_is_not_overridden(self):
        # audio_features approved; camera explicitly NOT approved.
        # The canonical gate (Track A fix) no longer sets the state-wide
        # flag as a side effect, and require_gated_modality checks the
        # per-record approval only. Even a manually-set state-wide flag
        # must not override the per-modality refusal.
        s = SessionGateState(mode="generic")
        record_modality_consent(s, "audio_features", attested_by="officer/a", jurisdiction="CO", jurisdiction_approved=True)
        record_modality_consent(s, "camera", attested_by="officer/a", jurisdiction="CO", jurisdiction_approved=False)
        self.assertFalse(s.jurisdiction_approved)  # no side effect
        s.jurisdiction_approved = True  # simulate a blanket approval
        with self.assertRaises(GateError) as ctx:
            require_live_modality(s, "camera")
        self.assertEqual(ctx.exception.code, "jurisdiction_approval_required")
        require_live_modality(s, "audio_features")  # approved record passes

    def test_audio_capture_consent_does_not_set_statewide_flag(self):
        s = SessionGateState(mode="generic")
        record_live_modality_consent(s, "audio_capture", attested_by="officer/a", jurisdiction="CO", jurisdiction_approved=True)
        self.assertFalse(s.jurisdiction_approved)
        self.assertTrue(live_modality_allowed(s, "audio_capture"))
        self.assertFalse(live_modality_allowed(s, "camera"))


class TestKillSwitchAndTimeline(unittest.TestCase):
    def _running(self):
        s = _state_with("audio_capture", "audio_features", "camera")
        ls = LiveSession(s, baseline_window_s=0)
        ls.start_audio()
        ls.start_video()
        return ls

    def test_kill_switch_stops_everything_and_session_still_seals(self):
        ls = self._running()
        ls.ingest_final_turn(_subject_turn("I was at home all evening with my family."))
        ls.set_timing_enabled(True)
        self.assertEqual(ls.status()["modalities"]["audio_features"], "ON")
        ls.kill_switch()
        st = ls.status()["modalities"]
        self.assertEqual(st["audio_capture"], "STOPPED BY OFFICER")
        self.assertEqual(st["camera"], "STOPPED BY OFFICER")
        self.assertEqual(st["audio_features"], "OFF", "kill switch must also stop timing cues")
        with self.assertRaises(GateError):
            ls.ingest_final_turn(_subject_turn("This turn must never be accepted."))
        reasons = [(e["event"], e["reason"]) for e in ls.timeline]
        self.assertIn(("stop", "officer_stop"), reasons)
        self.assertIn(("start", "officer_start"), reasons)
        pkg = ls.seal_package()
        self.assertTrue(verify_package_hash(pkg))
        self.assertEqual(pkg["live_inputs"]["session_id"], ls.session_id)
        self.assertTrue(pkg["live_inputs"]["timeline"])

    def test_per_modality_stop_leaves_audio_running(self):
        ls = self._running()
        ls.stop_modality("camera")
        self.assertEqual(ls.status()["modalities"]["camera"], "STOPPED BY OFFICER")
        self.assertEqual(ls.status()["modalities"]["audio_capture"], "ON")
        out = ls.ingest_final_turn(_subject_turn("Audio still flows after the camera stops."))
        self.assertIn("turn_index", out)
        with self.assertRaises(GateError):
            ls.ingest_video_window({"t_start_ms": 0, "t_end_ms": 30000, "frames_total": 10, "frames_tracked": 10})

    def test_sealed_timeline_is_inside_the_hash(self):
        ls = self._running()
        ls.ingest_final_turn(_subject_turn("I was at home all evening with my family."))
        ls.stop()
        pkg = ls.seal_package()
        self.assertTrue(verify_package_hash(pkg))
        pkg["live_inputs"]["timeline"].append({"event": "forged", "modality": "camera"})
        self.assertFalse(verify_package_hash(pkg), "tampering with the timeline must break the hash")


class TestTurnPipeline(unittest.TestCase):
    def _audio_session(self, with_timing=False):
        mods = ["audio_capture"] + (["audio_features"] if with_timing else [])
        s = _state_with(*mods)
        ls = LiveSession(s, baseline_window_s=0)
        ls.start_audio()
        return ls

    def test_typed_turn_flows_into_stream_pipeline(self):
        ls = self._audio_session()
        out = ls.ingest_final_turn(
            {"role": "subject", "text": "I am not sure, maybe it was Tuesday, I think."},
            source="typed",
        )
        self.assertEqual(out["turn_index"], 0)
        self.assertEqual(ls.transcript[0]["source"], "typed")
        self.assertEqual(ls.transcript[0]["stt_component"]["component_id"], "browser-speech-recognition")

    def test_unconfirmed_speaker_is_never_a_cue_source(self):
        ls = self._audio_session()
        out = ls.ingest_final_turn({"text": "maybe I am not sure, I think it was Tuesday"})
        self.assertTrue(ls.transcript[0]["speaker_unconfirmed"])
        self.assertEqual(out["cues"], [])
        self.assertEqual(ls.counters["turns_unconfirmed"], 1)

    def test_raw_media_turn_is_rejected(self):
        ls = self._audio_session()
        with self.assertRaises(ValueError):
            ls.ingest_final_turn({"role": "subject", "text": "hello", "pcm": b"\x00\x01"})
        self.assertEqual(ls.counters["turns_rejected_raw_media"], 1)
        self.assertEqual(len(ls.transcript), 0)

    def test_timing_cues_need_timing_consent(self):
        ls = self._audio_session(with_timing=False)
        for lat in (1000, 1100, 1050, 9000):
            ls.ingest_final_turn(_subject_turn("I was at home all evening with my family and friends.", latency_ms=lat))
        labels = {c["label"] for c in ls.cues_shown}
        self.assertFalse(labels & {"response_latency_anomaly_observed", "speech_rate_shift_observed", "pause_duration_elevated_observed"})
        self.assertEqual(ls.status()["modalities"]["audio_features"], "OFF")

    def test_timing_cues_need_baseline(self):
        # Timing on, but only 2 subject turns: baseline incomplete, no shift cue.
        s = _state_with("audio_capture", "audio_features")
        ls = LiveSession(s, baseline_window_s=0, baseline_min_turns=3)
        ls.start_audio()
        ls.set_timing_enabled(True)
        for lat in (1000, 9000):
            ls.ingest_final_turn(_subject_turn("I was at home all evening with my family and friends.", latency_ms=lat))
        labels = {c["label"] for c in ls.cues_shown}
        self.assertNotIn("response_latency_anomaly_observed", labels)
        self.assertFalse(ls.baseline_ready)

    def test_timing_cue_uses_template_wording_and_medium_ceiling(self):
        ls = self._audio_session(with_timing=True)
        for lat in (1000, 1100, 1050):
            ls.ingest_final_turn(_subject_turn("I was at home all evening with my family and friends.", latency_ms=lat))
        ls.set_timing_enabled(True)
        ls.ingest_final_turn(_subject_turn("I was at home all evening with my family and friends.", latency_ms=9000))
        timing = [c for c in ls.cues_shown if c["label"] == "response_latency_anomaly_observed"]
        self.assertEqual(len(timing), 1)
        cue = timing[0]
        self.assertEqual(cue["source"], "audio timing")
        self.assertEqual(cue["priority"], "medium")
        self.assertTrue(cue["message"].startswith("Response delay was longer than earlier in this interview (9.0 s against about 1.1 s)"))
        self.assertEqual(cue["caveat"], "Delays have many ordinary causes, such as recall effort, question difficulty or audio lag. Audio timing.")
        self.assertNotIn("aversion", cue["message"].lower())

    def test_timing_switch_can_be_turned_off_live(self):
        ls = self._audio_session(with_timing=True)
        ls.set_timing_enabled(True)
        self.assertEqual(ls.status()["modalities"]["audio_features"], "ON")
        ls.set_timing_enabled(False)
        self.assertEqual(ls.status()["modalities"]["audio_features"], "OFF")

    def test_chunk_duplicate_and_gap_are_recorded(self):
        ls = self._audio_session()
        self.assertEqual(ls.ingest_audio_chunk(0, 3200), {"ack": 0})
        self.assertEqual(ls.ingest_audio_chunk(0, 3200), {"ack": 0, "dup": True})
        self.assertEqual(ls.counters["chunks_duplicate"], 1)
        ls.ingest_audio_chunk(2, 3200)  # seq 1 missing
        self.assertEqual(ls.counters["chunks_gap"], 1)
        self.assertGreater(ls.counters["gap_filled_ms"], 0)


class TestCueWording(unittest.TestCase):
    def test_timing_templates(self):
        lat = format_timing_cue({"label": "response_latency_anomaly_observed",
                                 "evidence": {"latency_ms": 9000, "baseline_median_ms": 1100, "direction": "longer", "t_media_ms": 65000}})
        self.assertEqual(lat["message"], "Response delay was longer than earlier in this interview (9.0 s against about 1.1 s), around 01:05.")
        rate = format_timing_cue({"label": "speech_rate_shift_observed",
                                  "evidence": {"wpm": 210, "baseline_median_wpm": 140, "direction": "faster", "t_start_ms": 0, "t_end_ms": 30000}})
        self.assertIn("Speech rate was higher than earlier in this interview (210 against about 140 words per minute) between 00:00 and 00:30.", rate["message"])
        pause = format_timing_cue({"label": "pause_duration_elevated_observed",
                                   "evidence": {"t_start_ms": 60000, "t_end_ms": 90000}})
        self.assertIn("Pauses within answers were more frequent than earlier in this interview between 01:00 and 01:30.", pause["message"])
        self.assertIsNone(format_timing_cue({"label": "not_a_timing_label", "evidence": {}}))

    def test_video_templates_use_off_camera_gaze(self):
        gaze = format_video_cue("gaze_pattern_shift_observed", direction="higher", t_start_ms=0, t_end_ms=30000)
        self.assertIn("Gaze was directed away from the camera more often than earlier in this interview between 00:00 and 00:30.", gaze["message"])
        self.assertIn("Video-derived, low confidence.", gaze["caveat"])
        self.assertNotIn("aversion", gaze["message"].lower())
        self.assertIsNone(format_video_cue("not_a_video_label", direction="higher", t_start_ms=0, t_end_ms=1))

    def test_gaze_observer_wording(self):
        turns = [{"role": "subject", "text": "x", "off_camera_gaze_share": v} for v in (0.10, 0.12, 0.11, 0.90)]
        obs = GazePatternObserver().observe(turns).to_dicts()
        self.assertEqual(len(obs), 1)
        self.assertIn("Off-camera gaze was higher than baseline", obs[0]["cue"])
        self.assertIn("off_camera_gaze_share", obs[0]["evidence"])
        self.assertNotIn("gaze_aversion_ratio", obs[0]["evidence"])

    def test_live_timing_hook_requires_consent(self):
        s = SessionGateState(mode="generic")
        hook = LiveAudioTimingHook(state=s, require_consent_check=True)
        with self.assertRaises(Exception):
            hook.push_turn({"role": "subject", "text": "hi", "response_latency_ms": 3000})
        s2 = _state_with("audio_features")
        hook2 = LiveAudioTimingHook(state=s2, require_consent_check=True)
        self.assertIsInstance(hook2.push_turn({"role": "subject", "text": "hi", "response_latency_ms": 1000}), list)

    def test_timing_only_observers_exclude_prosody(self):
        s = _state_with("audio_features")
        turns = [{"role": "subject", "text": "a b c d", "pitch_variance": 99.0, "jitter": 5.0,
                  "response_latency_ms": 1000, "duration_ms": 3000}] * 4
        obs = observe_live_audio_timing(turns, state=s)
        labels = {o["label"] for o in obs}
        self.assertFalse(labels & {"prosodic_variability_shift_observed", "acoustic_feature_shift_observed"})


class TestVideoWindows(unittest.TestCase):
    def _video_session(self):
        s = _state_with("audio_capture", "camera")
        ls = LiveSession(s, baseline_window_s=0)
        ls.start_video()
        return ls

    def _window(self, t0, gaze=None, blink=None, movement=None):
        return {"t_start_ms": t0, "t_end_ms": t0 + 30000, "frames_total": 60, "frames_tracked": 60,
                "off_camera_gaze_share": gaze, "blink_count": blink, "movement_index": movement}

    def test_video_cues_are_lowest_priority(self):
        ls = self._video_session()
        for i, gaze in enumerate((0.10, 0.12, 0.11, 0.90)):
            out = ls.ingest_video_window(self._window(i * 30000, gaze=gaze, movement=0.5))
        cues = [c for c in ls.cues_shown if c["source"] == "video-derived"]
        self.assertTrue(cues, "expected a video-derived cue from the gaze shift")
        for c in cues:
            self.assertEqual(c["priority"], "low")
            self.assertIn("Video-derived, low confidence.", c["caveat"])
        gaze_cues = [c for c in cues if c["label"] == "gaze_pattern_shift_observed"]
        self.assertEqual(len(gaze_cues), 1)
        self.assertIn("Gaze was directed away from the camera more often", gaze_cues[0]["message"])

    def test_video_window_schema_rejects_frames_and_forbidden_fields(self):
        with self.assertRaises(ValueError):
            VideoWindow.from_dict({"t_start_ms": 0, "t_end_ms": 1, "frames_total": 1, "frames_tracked": 1,
                                   "frame_bytes": b"\x00\x01"})
        with self.assertRaises(ValueError):
            VideoWindow.from_dict({"t_start_ms": 0, "t_end_ms": 1, "frames_total": 1, "frames_tracked": 1,
                                   "emotion": "happy"})
        w = VideoWindow.from_dict(self._window(0, gaze=0.1))
        self.assertEqual(w.tracking_quality, 1.0)
        self.assertNotIn("frame", w.to_dict())

    def test_no_frames_in_sealed_package(self):
        ls = self._video_session()
        for i in range(4):
            ls.ingest_video_window(self._window(i * 30000, gaze=0.1 + i * 0.01, movement=0.5))
        pkg = ls.seal_package()
        blob = json.dumps(pkg, default=str)
        for banned in ("frame_bytes", "pixels", "landmarks", "embedding", "per_frame"):
            self.assertNotIn(banned, blob)
        self.assertTrue(verify_package_hash(pkg))
        self.assertEqual(len(pkg["live_inputs"]["video_windows"]), 4)

    def test_low_tracking_quality_produces_state_not_cue(self):
        ls = self._video_session()
        out = ls.ingest_video_window({"t_start_ms": 0, "t_end_ms": 30000, "frames_total": 60,
                                      "frames_tracked": 5, "off_camera_gaze_share": 0.9,
                                      "blink_count": None, "movement_index": None})
        self.assertEqual(out["state"], "Tracking quality too low")
        self.assertEqual(out["cues"], [])


class TestSttAdapters(unittest.TestCase):
    def test_browser_stt_is_the_default_and_bundles_no_model(self):
        desc = BrowserSttAdapter().describe()
        self.assertEqual(desc["component_id"], "browser-speech-recognition")
        self.assertIn("no bundled model", desc["model_id"].lower())
        self.assertIsNone(desc["model_sha256"])

    def test_local_adapter_names_the_missing_extra(self):
        with self.assertRaises(SttNotAvailable) as ctx:
            vosk_adapter().describe()
        self.assertIn("live-audio", str(ctx.exception))

    def test_cloud_transcription_fails_closed(self):
        cloud = CloudSttAdapter()
        self.assertFalse(cloud.is_configured())
        with self.assertRaises(CloudSttNotConfigured):
            cloud.describe()
        with self.assertRaises(CloudSttNotConfigured):
            cloud.configure(provider="example", endpoint="https://example.invalid", explicit_opt_in=False)
        cloud.configure(provider="customer-private-stt", endpoint="https://stt.internal.example", explicit_opt_in=True)
        self.assertTrue(cloud.is_configured())
        self.assertEqual(cloud.describe()["provider"], "customer-private-stt")


class TestLiveServer(unittest.TestCase):
    def _started_server(self):
        s = _state_with("audio_capture")
        ls = LiveSession(s, baseline_window_s=0)
        srv = LiveAvServer(ls)
        srv.start()
        self.addCleanup(srv.stop)
        return ls, srv

    def _req(self, url, *, method="GET", body=None, token=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if body is not None:
            req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("X-Ingest-Token", token)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_page_requires_token_and_shows_kill_switch(self):
        ls, srv = self._started_server()
        status, _ = self._req(srv.url.split("?")[0])
        self.assertEqual(status, 401)
        status, body = self._req(srv.url)
        self.assertEqual(status, 200)
        self.assertIn(b"KILL SWITCH", body)
        self.assertIn(b"officer only", body.lower())

    def test_turn_ingest_requires_token_and_running_audio(self):
        ls, srv = self._started_server()
        base = f"http://127.0.0.1:{srv.port}/live/v1/{ls.session_id}"
        status, _ = self._req(base + "/turn", method="POST",
                              body={"role": "subject", "text": "hello"}, token=None)
        self.assertEqual(status, 401)
        status, body = self._req(base + "/turn", method="POST",
                                 body={"role": "subject", "text": "hello"}, token=ls.ingest_token)
        self.assertEqual(status, 403)  # audio not started yet
        status, _ = self._req(base + "/start", method="POST",
                              body={"modality": "audio_capture"}, token=ls.ingest_token)
        self.assertEqual(status, 200)
        status, body = self._req(base + "/turn", method="POST",
                                 body={"role": "subject", "text": "I was at home all evening."},
                                 token=ls.ingest_token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["turn_index"], 0)
        status, body = self._req(base + "/state?token=" + ls.ingest_token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["modalities"]["audio_capture"], "ON")

    def test_raw_media_turn_rejected_by_server(self):
        ls, srv = self._started_server()
        base = f"http://127.0.0.1:{srv.port}/live/v1/{ls.session_id}"
        self._req(base + "/start", method="POST", body={"modality": "audio_capture"}, token=ls.ingest_token)
        status, _ = self._req(base + "/turn", method="POST",
                              body={"role": "subject", "text": "hi", "pcm": "AAE="}, token=ls.ingest_token)
        self.assertEqual(status, 400)

    def test_kill_switch_over_http(self):
        ls, srv = self._started_server()
        base = f"http://127.0.0.1:{srv.port}/live/v1/{ls.session_id}"
        self._req(base + "/start", method="POST", body={"modality": "audio_capture"}, token=ls.ingest_token)
        status, body = self._req(base + "/stop", method="POST", body={"reason": "officer_stop"}, token=ls.ingest_token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["modalities"]["audio_capture"], "STOPPED BY OFFICER")


@pytest.mark.skipif(not FACE_AVAILABLE, reason="face extra not installed (pip install 'cueliez[face]')")
class TestLiveFaceMatching(unittest.TestCase):
    def _face_session(self):
        s = _state_with("face_recognition")
        ls = LiveSession(s, baseline_window_s=0)
        ls.enable_face_recognition()
        return ls

    def _img(self, name):
        return (FIXTURES / name).read_bytes()

    def test_enroll_and_match_real_images(self):
        ls = self._face_session()
        enrolled = ls.enroll_face("obama", self._img("obama.jpg"))
        self.assertEqual(enrolled["subject_id"], "obama")
        self.assertTrue(enrolled["aligned"])
        same2 = ls.match_face(self._img("obama2.jpg"))
        same3 = ls.match_face(self._img("obama3.jpg"))
        self.assertTrue(same2["matched"], same2)
        self.assertEqual(same2["subject_id"], "obama")
        self.assertLess(same2["distance"], 0.9)
        self.assertTrue(same3["matched"], same3)
        self.assertLess(same3["distance"], 0.9)
        other = ls.match_face(self._img("biden.jpg"))
        other2 = ls.match_face(self._img("biden2.jpg"))
        self.assertFalse(other["matched"], other)
        self.assertIsNone(other["subject_id"])
        self.assertGreater(other["distance"], 0.9)
        self.assertFalse(other2["matched"], other2)
        self.assertEqual(ls.counters["face_matches"], 4)
        self.assertEqual(ls.counters["face_match_hits"], 2)

    def test_match_with_no_enrollment_is_not_a_match(self):
        ls = self._face_session()
        result = ls.match_face(self._img("obama.jpg"))
        self.assertFalse(result["matched"])
        self.assertIsNone(result["subject_id"])
        self.assertIsNone(result["distance"])

    def test_enroll_rejects_image_with_no_face(self):
        ls = self._face_session()
        with self.assertRaises(FaceRecError) as ctx:
            ls.enroll_face("nobody", _white_png_bytes())
        self.assertEqual(ctx.exception.code, "face_not_found")
        # Matching a faceless probe against an enrolled subject also fails closed.
        ls.enroll_face("obama", self._img("obama.jpg"))
        with self.assertRaises(FaceRecError) as ctx:
            ls.match_face(_white_png_bytes())
        self.assertEqual(ctx.exception.code, "face_not_found")

    def test_templates_deleted_when_face_matching_stops(self):
        ls = self._face_session()
        ls.enroll_face("obama", self._img("obama.jpg"))
        self.assertEqual(ls._face_store.enrolled_subjects(), ["obama"])
        ls.stop_modality("face_recognition")
        self.assertIsNone(ls._face_store)
        with self.assertRaises(GateError):
            ls.match_face(self._img("obama2.jpg"))

    def test_face_events_are_in_the_sealed_timeline(self):
        ls = self._face_session()
        ls.enroll_face("obama", self._img("obama.jpg"))
        ls.match_face(self._img("obama2.jpg"))
        pkg = ls.seal_package()
        kinds = [e["event"] for e in pkg["live_inputs"]["timeline"]]
        self.assertIn("face_enroll", kinds)
        self.assertIn("face_match", kinds)
        self.assertTrue(verify_package_hash(pkg))
        blob = json.dumps(pkg, default=str)
        self.assertNotIn("image_bytes", blob)
        self.assertEqual(pkg["live_inputs"]["components"]["face_matching"]["backend"],
                         "openface/nn4.small2.v1.t7 (opencv-contrib)")


@pytest.mark.skipif(FACE_AVAILABLE, reason="only meaningful when the face extra is absent")
class TestFaceRecUnavailable(unittest.TestCase):
    def test_missing_backend_fails_closed_naming_the_extra(self):
        from cueliez.live_av import get_face_recognizer

        with self.assertRaises(FaceRecError) as ctx:
            get_face_recognizer()
        self.assertIn("cueliez[face]", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
