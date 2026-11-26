"""Live audio/video surface for CueLiez (Phase 10, Track D).

Officer-only live capture: microphone -> browser speech recognition ->
finalised turns into the existing ``--stream-turns`` runner path; derived
audio-timing cues (latency, speech rate, pauses) under a separate consent;
live video as derived numeric features only; real face matching behind its
own consent gate (see :mod:`cueliez.live_av` face section below).

What is real here, and what is not
-----------------------------------
* Real (stdlib + browser APIs): the HTTP ingest server, the per-modality
  consent gate, the kill switch, the modality/state timeline, the
  turn pipeline (the existing ``default_runner`` plus the timing-only
  observers), the browser capture page (``getUserMedia`` + the browser
  SpeechRecognition API for speech-to-text, canvas frame differencing
  for a movement index), and face matching through an installed
  recognizer backend (see ``get_face_recognizer``).
* Not bundled, not claimed: no speech-to-text model ships with CueLiez.
  The default speech path is the browser's own SpeechRecognition
  implementation. A local model adapter interface exists
  (``ExtraSttAdapter``) for Vosk / faster-whisper, but no model is
  installed, downloaded, or claimed present.
* Cloud transcription is NOT enabled by default and no provider is
  bundled. ``CloudSttAdapter`` is a gated opt-in interface only and
  fails closed (``CloudSttNotConfigured``) until an operator explicitly
  configures a provider.
* Video gaze/blink features are NOT computed by the capture page: no
  face model is bundled in the browser. The page reports them as not
  computed and the server treats windows without face tracking as
  "Tracking quality too low". Movement is computed for real in the
  page by frame differencing. A MediaPipe/OpenCV extractor remains a
  future optional extra; nothing here fakes its numbers.

Phase B entry gate (owner/PM decision, still open)
--------------------------------------------------
Production use of the video-derived features requires, before it
ships: counsel answers for the pilot jurisdiction, a literature
review of gaze/blink/movement indicators with cited sources, and an
over-cue report on consenting neutral sessions reviewed by the
owner. This module implements the plumbing behind that gate; it does
not claim the gate has been met.

Face matching (real, gated, sensitive data)
-------------------------------------------
Enrollment + matching delegate to Track B's observer
(``cueliez.observations.face_recognition``): Haar detection,
FacemarkLBF alignment, OpenFace nn4.small2.v1.t7 128-d embeddings,
Euclidean-distance matching at threshold 0.9. No match score is
ever invented here: without the installed ``face`` extra every call
raises ``FaceRecError`` naming the missing optional extra. Templates
are numeric embeddings only -- no image bytes are retained -- held
in memory by default, transmitted nowhere by default, and deleted
on ``close()`` / ``delete_subject()`` unless the operator explicitly
opts into persistence with face-recognition consent recorded.
Matching runs on the capture host (this server binds loopback by
default); a still sent to ``/face-match`` is decoded in memory and
discarded, never written to disk.

Demographic inference is NOT part of this module. It stays behind
its own separate gate (owner clarification, Nov 25, 2026) and is not
folded into the general modality gate here.

Language: observations and cues only. Cue text follows the product
templates in ``docs/design/LIVE_AV_PRODUCT_SCOPE.md`` section 4.2.
Video wording is "off-camera gaze" throughout.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import secrets
import statistics
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib.parse import urlparse

from .gates import (
    GATED_INPUT_MODALITIES,
    GateError,
    SessionGateState,
    record_modality_consent as _canonical_record_modality_consent,
    require_consent,
    require_gated_modality,
    require_training,
)
from .observations.audio_path import observe_live_audio_timing
from .observations.base import is_subject_turn
from .observations.behavioral import ResponseLatencyObserver, SpeechRateShiftObserver
from .observations.prosody import PausePatternObserver
from .observations.runner import default_runner
from .observations.visual import BlinkRateObserver, GazePatternObserver
from .delivery.events import cues_from_observations
from .session import seal as _seal_package

__all__ = [
    "LiveSession",
    "LiveAvServer",
    "VideoWindow",
    "FaceMatchResult",
    "LiveFaceStore",
    "FaceTemplateStore",  # alias of LiveFaceStore (Track B owns the canonical name)
    "get_face_recognizer",
    "available_face_rec_backends",
    "FaceRecError",
    "SttNotAvailable",
    "CloudSttNotConfigured",
    "BrowserSttAdapter",
    "ExtraSttAdapter",
    "CloudSttAdapter",
    "require_live_modality",
    "record_live_modality_consent",
    "format_timing_cue",
    "format_video_cue",
    "LIVE_ALLOWED_MODES",
    "LIVE_MODALITY_KEYS",
    "TIMING_CAVEATS",
    "VIDEO_CAVEATS",
    "RAW_MEDIA_KEYS",
]

LIVE_AV_VERSION = "1.0"
CONSENT_TEXT_VERSION = "live-av-consent-v1"
LIVE_TRAINING_VERSION = "live-av-training-v1"

# Live inputs are refused in these modes (product scope 1.4).
LIVE_ALLOWED_MODES = frozenset({"generic", "interrogation"})
LIVE_REFUSED_MODES = frozenset({"government", "clinical", "therapy"})

# Canonical modality keys for the live surface. "audio_timing" is the
# product name for the existing "audio_features" key.
LIVE_MODALITY_KEYS = frozenset({"audio_capture", "audio_features", "camera", "face_recognition"})
MODALITY_ALIASES = {
    "audio_timing": "audio_features",
    "audio-features": "audio_features",
    "audio_capture": "audio_capture",
    "audio-capture": "audio_capture",
    "mic": "audio_capture",
    "microphone": "audio_capture",
    "camera": "camera",
    "video": "camera",
    "face_recognition": "face_recognition",
    "face-recognition": "face_recognition",
    "face_rec": "face_recognition",
    "face-rec": "face_recognition",
}

# Keys whose presence in an ingested turn means raw media was sent. Such
# turns are rejected outright; the live package never holds media bytes.
RAW_MEDIA_KEYS = frozenset({
    "audio", "audio_bytes", "pcm", "samples", "waveform", "audio_samples",
    "frame", "frame_bytes", "image", "image_bytes", "pixels", "landmarks",
    "embedding", "face_image", "video_frame",
})

# Observation labels that belong to the separately-consented timing path.
TIMING_LABELS = frozenset({
    "response_latency_anomaly_observed",
    "speech_rate_shift_observed",
    "pause_duration_elevated_observed",
})
# Labels the live text path must never emit without their own consent.
PROSODY_LABELS = frozenset({
    "prosodic_variability_shift_observed",
    "acoustic_feature_shift_observed",
})
VISUAL_LABELS = frozenset({
    "gaze_pattern_shift_observed",
    "blink_rate_shift_observed",
    "motor_activity_shift_observed",
})

TIMING_CAVEATS = {
    "response_latency_anomaly_observed":
        "Delays have many ordinary causes, such as recall effort, question difficulty or audio lag. Audio timing.",
    "speech_rate_shift_observed":
        "Speech rate varies with topic, language and comfort with the setting. Audio timing.",
    "pause_duration_elevated_observed":
        "Pauses have many ordinary causes. Audio timing.",
}
VIDEO_CAVEATS = {
    "gaze_pattern_shift_observed":
        "Gaze habits vary by culture, comfort, disability and where the camera sits relative to the screen. Video-derived, low confidence.",
    "blink_rate_shift_observed":
        "Blink rate varies with fatigue, lighting, dry eyes and contact lenses. Video-derived, low confidence.",
    "motor_activity_shift_observed":
        "Movement varies with posture, seating and room conditions. Video-derived, low confidence.",
}

# Fixed product-scope templates (section 4.2). Only these shapes are used
# for live-input cue text; the fixed caveat is always appended.
NOT_ENOUGH_BASELINE = "Not enough baseline yet for {indicator}."
TRACKING_TOO_LOW = "Tracking quality too low for {indicator}."

_BANNED_LIVE_TERMS = (
    "nervous", "anxious", "stressed", "tense", "uncomfortable", "evasive",
    "avoiding", "hiding", "guarded", "suspicious", "deceptive", "truthful",
    "sincere", "confident", "defensive", "micro-expression", "red flag",
    "credibility", "reliability",
)


def _check_live_text(text: str) -> None:
    low = (text or "").lower()
    for term in _BANNED_LIVE_TERMS:
        if term in low:
            raise ValueError(f"live cue text uses a banned term: {term!r}")


def _fmt_mmss(t_media_ms: Optional[float]) -> str:
    if t_media_ms is None:
        return "?:??"
    total = max(0, int(t_media_ms // 1000))
    return f"{total // 60:02d}:{total % 60:02d}"


def _fmt_seconds(value_ms: float) -> str:
    return f"{value_ms / 1000.0:.1f}"


# ---------------------------------------------------------------------------
# Per-modality consent (live-surface view of the gate state)
# ---------------------------------------------------------------------------

def _normalize_modality(modality: str) -> str:
    key = (modality or "").strip().lower().replace(" ", "_")
    if key in MODALITY_ALIASES:
        return MODALITY_ALIASES[key]
    return key


def _strict_record_check(state: Any, key: str) -> None:
    """Strict per-record consent + jurisdiction check.

    Does NOT fall back to the state-wide ``jurisdiction_approved``
    flag: a per-modality record marked not approved must stay refused
    even when another modality was approved. The canonical gate now
    enforces the same rule (Track A fix for the earlier override gap);
    this keeps the strict rule as defense-in-depth on the live path.
    """
    consents = getattr(state, "modality_consents", None)
    if consents is None and isinstance(state, dict):
        consents = state.get("modality_consents") or {}
    rec = (consents or {}).get(key)
    if not rec or not rec.get("consented"):
        raise GateError(
            "modality_consent_required",
            f"Explicit consent is required before enabling gated input modality {key!r}.",
        )
    att = (rec.get("attested_by") or "").strip()
    if not att:
        att_state = getattr(state, "consent_attested_by", None) or (state.get("consent_attested_by") if isinstance(state, dict) else None) or ""
        if not str(att_state).strip():
            raise GateError(
                "consent_attester_required",
                f"Non-empty attester is required for gated input modality {key!r}.",
            )
    jur = (rec.get("jurisdiction") or "").strip()
    if not jur:
        jur_state = getattr(state, "jurisdiction", None) or (state.get("jurisdiction") if isinstance(state, dict) else None) or ""
        if not str(jur_state).strip():
            raise GateError(
                "jurisdiction_required",
                f"Jurisdiction must be recorded before enabling gated input modality {key!r}.",
            )
    if not bool(rec.get("jurisdiction_approved")):
        raise GateError(
            "jurisdiction_approval_required",
            f"Jurisdiction approval is required before enabling gated input modality {key!r}.",
        )


def require_live_modality(state: Any, modality: str) -> None:
    """Fail closed: explicit per-modality consent + jurisdiction approval.

    Works for canonical gated keys (``audio_features``, ``camera``) and
    for live keys the canonical gate does not yet carry
    (``audio_capture``, ``face_recognition`` -- Track A owns adding those
    to ``gates.GATED_INPUT_MODALITIES``; until then the record is read
    directly from ``state.modality_consents`` with the same strict
    rules). Raises :class:`GateError` on any failure.
    """
    if state is None:
        raise GateError("gate_state_required", "Session gate state is required before enabling a live modality.")
    key = _normalize_modality(modality)
    if key not in LIVE_MODALITY_KEYS:
        raise GateError("modality_invalid", f"Unknown live modality {modality!r}.")
    if key in GATED_INPUT_MODALITIES:
        require_gated_modality(state, key)
        _strict_record_check(state, key)
        return
    _strict_record_check(state, key)


def record_live_modality_consent(
    state: SessionGateState,
    modality: str,
    *,
    attested_by: str,
    jurisdiction: Optional[str] = None,
    jurisdiction_approved: bool = True,
) -> None:
    """Record explicit consent + jurisdiction approval for a live modality.

    Canonical keys delegate to ``gates.record_modality_consent``. Keys
    the canonical gate does not yet carry (``audio_capture``,
    ``face_recognition``) are recorded in the same shape directly on
    ``state.modality_consents`` -- without the state-wide
    ``jurisdiction_approved`` side effect, so one modality's approval
    never silently enables another.
    """
    key = _normalize_modality(modality)
    if key not in LIVE_MODALITY_KEYS:
        raise GateError("modality_invalid", f"Unknown live modality {modality!r}.")
    who = (attested_by or "").strip()
    if not who:
        raise GateError("consent_attester_required", "attested_by must be a non-empty identifier for modality consent.")
    if key in GATED_INPUT_MODALITIES:
        _canonical_record_modality_consent(
            state, key, attested_by=who, jurisdiction=jurisdiction,
            jurisdiction_approved=jurisdiction_approved,
        )
        return
    if jurisdiction is not None:
        state.jurisdiction = (jurisdiction or "").strip() or state.jurisdiction
    state.modality_consents[key] = {
        "consented": True,
        "attested_by": who,
        "jurisdiction": state.jurisdiction,
        "jurisdiction_approved": bool(jurisdiction_approved),
        "recorded_at": time.time(),
    }


def live_modality_allowed(state: Any, modality: str) -> bool:
    try:
        require_live_modality(state, modality)
        return True
    except GateError:
        return False


def _require_live_mode(state: Any) -> None:
    mode = getattr(state, "mode", None) or (state.get("mode") if isinstance(state, dict) else None) or "generic"
    if mode in LIVE_REFUSED_MODES:
        raise GateError(
            "live_mode_refused",
            f"Live audio/video inputs are refused in mode={mode!r}.",
        )
    if mode not in LIVE_ALLOWED_MODES:
        raise GateError("live_mode_refused", f"Live audio/video inputs are refused in mode={mode!r}.")
    if isinstance(state, SessionGateState):
        require_consent(state, action="start live inputs")
        require_training(state)


# ---------------------------------------------------------------------------
# Speech-to-text adapters
# ---------------------------------------------------------------------------

class SttNotAvailable(Exception):
    """A local speech-to-text adapter is not installed."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class CloudSttNotConfigured(Exception):
    """Cloud transcription was requested but no provider is configured."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BrowserSttAdapter:
    """The browser's own SpeechRecognition implementation.

    This is the default (and only bundled) speech path: the capture page
    runs recognition in the officer's browser and posts finalised text
    to this server. No model ships with CueLiez; accuracy, language
    support and availability depend on the browser. Audio never leaves
    the browser except as finalised text posted to the local server.
    """

    component_id = "browser-speech-recognition"
    version = "browser-provided"
    model_id = "browser SpeechRecognition (no bundled model)"
    model_sha256: Optional[str] = None

    def is_available(self) -> bool:
        # Availability is a browser property; the server cannot verify it.
        # The capture page reports support (or its absence) at runtime.
        return True

    def describe(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "version": self.version,
            "model_id": self.model_id,
            "model_sha256": None,
            "kind": "browser",
            "note": "Speech recognition runs in the officer browser; no model is bundled with CueLiez.",
        }


class ExtraSttAdapter:
    """Local-model speech adapter interface (Vosk / faster-whisper).

    No model is bundled. The adapter reports itself unavailable until
    the named optional extra is installed, and names the extra in the
    error so the operator knows exactly what to install. A future
    implementation plugs a real engine behind ``open``/``accept``.
    """

    def __init__(self, *, extra_name: str, component_id: str, install_hint: str):
        self.extra_name = extra_name
        self.component_id = component_id
        self.version: Optional[str] = None
        self.model_id: Optional[str] = None
        self.model_sha256: Optional[str] = None
        self.install_hint = install_hint

    def is_available(self) -> bool:
        return False

    def describe(self) -> Dict[str, Any]:
        raise SttNotAvailable(
            "stt_extra_missing",
            f"Local speech-to-text adapter {self.component_id!r} is not installed. {self.install_hint}",
        )

    def open(self, *, sample_rate: int = 16000, channels: int = 1):  # pragma: no cover - guarded by describe()
        self.describe()


def vosk_adapter() -> ExtraSttAdapter:
    return ExtraSttAdapter(
        extra_name="live-audio",
        component_id="vosk",
        install_hint="Install the optional extra (pip install 'cueliez[live-audio]') and supply a Vosk model; record its model id and sha256 in the sealed package.",
    )


def faster_whisper_adapter() -> ExtraSttAdapter:
    return ExtraSttAdapter(
        extra_name="live-audio-whisper",
        component_id="faster-whisper",
        install_hint="Install the optional extra (pip install 'cueliez[live-audio-whisper]') and supply a faster-whisper model; record its model id and sha256 in the sealed package.",
    )


class CloudSttAdapter:
    """Gated opt-in cloud transcription interface. Not configured by default.

    No cloud provider is bundled and no audio is sent anywhere by this
    class until an operator explicitly calls :meth:`configure` with a
    provider inside the customer's own environment. Every call before
    that raises :class:`CloudSttNotConfigured` (fail closed).
    """

    def __init__(self):
        self.provider: Optional[str] = None
        self.endpoint: Optional[str] = None
        self._configured = False

    def is_configured(self) -> bool:
        return self._configured

    def configure(self, *, provider: str, endpoint: str, explicit_opt_in: bool = False) -> None:
        """Explicitly configure a private-environment transcription service.

        ``explicit_opt_in`` must be True; anything else refuses. The
        choice is recorded in the sealed package by the caller.
        """
        if not explicit_opt_in:
            raise CloudSttNotConfigured(
                "Cloud transcription requires an explicit opt-in configuration; refusing to enable by default."
            )
        if not (provider or "").strip() or not (endpoint or "").strip():
            raise CloudSttNotConfigured("Cloud transcription needs a provider name and an endpoint inside the customer environment.")
        self.provider = provider.strip()
        self.endpoint = endpoint.strip()
        self._configured = True

    def describe(self) -> Dict[str, Any]:
        if not self._configured:
            raise CloudSttNotConfigured(
                "Cloud transcription is not configured: no provider is bundled and none has been configured."
            )
        return {"component_id": "cloud-stt", "provider": self.provider, "endpoint": self.endpoint}

    def transcribe(self, audio_bytes: bytes):  # pragma: no cover - no provider exists to call
        self.describe()
        raise CloudSttNotConfigured("Cloud transcription is not configured: no provider is bundled.")


# ---------------------------------------------------------------------------
# Video windows: derived numeric aggregates only (Phase B)
# ---------------------------------------------------------------------------

VIDEO_WINDOW_FIELDS = frozenset({
    "t_start_ms", "t_end_ms", "frames_total", "frames_tracked",
    "off_camera_gaze_share", "blink_count", "movement_index",
})
# Fields that must never appear in a video window: anything that could
# carry pixels, per-frame series, identity, or expression content.
VIDEO_FORBIDDEN_FIELDS = frozenset({
    "frame", "frames", "frame_bytes", "image", "pixels", "landmarks",
    "embedding", "blendshape", "emotion", "expression", "identity",
    "demographic", "age", "gender", "per_frame", "series",
})


@dataclass(frozen=True)
class VideoWindow:
    """One window of derived video features. No pixels, no per-frame series.

    ``off_camera_gaze_share`` / ``blink_count`` are None when no face
    model is available (the browser capture page reports them as not
    computed); ``movement_index`` is computed for real in the page by
    frame differencing. ``frames_tracked`` counts frames where a face
    was tracked; windows below the tracking minimum produce no cue.
    """

    t_start_ms: float
    t_end_ms: float
    frames_total: int
    frames_tracked: int
    off_camera_gaze_share: Optional[float] = None
    blink_count: Optional[int] = None
    movement_index: Optional[float] = None

    @property
    def tracking_quality(self) -> float:
        if not self.frames_total:
            return 0.0
        return max(0.0, min(1.0, self.frames_tracked / self.frames_total))

    @property
    def duration_ms(self) -> float:
        return max(0.0, float(self.t_end_ms) - float(self.t_start_ms))

    def blink_rate_per_min(self) -> Optional[float]:
        if self.blink_count is None or self.duration_ms <= 0:
            return None
        return self.blink_count / (self.duration_ms / 60000.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "t_start_ms": self.t_start_ms,
            "t_end_ms": self.t_end_ms,
            "frames_total": self.frames_total,
            "frames_tracked": self.frames_tracked,
            "off_camera_gaze_share": self.off_camera_gaze_share,
            "blink_count": self.blink_count,
            "movement_index": self.movement_index,
            "tracking_quality": round(self.tracking_quality, 4),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VideoWindow":
        if not isinstance(data, Mapping):
            raise ValueError("video window must be a JSON object")
        unknown = set(data) - VIDEO_WINDOW_FIELDS
        forbidden = unknown & VIDEO_FORBIDDEN_FIELDS
        if forbidden:
            raise ValueError(f"video window carries forbidden fields: {sorted(forbidden)}")
        if unknown:
            raise ValueError(f"video window carries unknown fields: {sorted(unknown)}")
        for req in ("t_start_ms", "t_end_ms", "frames_total", "frames_tracked"):
            if req not in data:
                raise ValueError(f"video window is missing required field: {req}")
        gaze = data.get("off_camera_gaze_share")
        if gaze is not None and not (0.0 <= float(gaze) <= 1.0):
            raise ValueError("off_camera_gaze_share must be in [0, 1]")
        blink = data.get("blink_count")
        if blink is not None and int(blink) < 0:
            raise ValueError("blink_count must be >= 0")
        return cls(
            t_start_ms=float(data["t_start_ms"]),
            t_end_ms=float(data["t_end_ms"]),
            frames_total=int(data["frames_total"]),
            frames_tracked=int(data["frames_tracked"]),
            off_camera_gaze_share=None if gaze is None else float(gaze),
            blink_count=None if blink is None else int(blink),
            movement_index=None if data.get("movement_index") is None else float(data["movement_index"]),
        )


# ---------------------------------------------------------------------------
# Face matching: live-surface delegate over Track B's observer
# ---------------------------------------------------------------------------
# Track B owns the recognizer itself (src/cueliez/observations/
# face_recognition.py): Haar detection, FacemarkLBF alignment, OpenFace
# nn4.small2.v1.t7 128-d embeddings, Euclidean-distance matching. This
# module does NOT re-implement enrollment or matching -- it adds only the
# live-surface concerns: image-bytes decoding, consent-gated enablement,
# session-scoped in-memory templates, and the HTTP endpoints. Every
# distance and score reported here comes from Track B's observer.
# A dlib/face_recognition backend was evaluated first and set aside: no
# wheel is published for this Python/platform, the source build needs
# cmake + a C++ toolchain and gigabytes of build space, and Track B's
# OpenCV/OpenFace path already works here with measured separation on
# real portraits. An OpenCV LBPH fallback was likewise set aside for
# the same reason (it would duplicate Track B's observer).

FACE_MODEL_ENV = "CUELIEZ_FACE_MODEL_PATH"
FACE_LANDMARK_ENV = "CUELIEZ_FACE_LANDMARK_MODEL_PATH"


class FaceRecError(Exception):
    """Face matching is unavailable or refused (fail closed)."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


@dataclass(frozen=True)
class FaceMatchResult:
    subject_id: Optional[str]
    distance: Optional[float]
    confidence: float
    threshold: float
    backend: str
    model_id: str
    matched: bool
    faces_found: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "distance": None if self.distance is None else round(float(self.distance), 4),
            "confidence": round(float(self.confidence), 4),
            "threshold": self.threshold,
            "backend": self.backend,
            "model_id": self.model_id,
            "matched": bool(self.matched),
            "faces_found": self.faces_found,
            # A match is an observation for officer review, never a finding.
            "epistemic_note": "Face match is a probabilistic observation for officer review, not an identification finding.",
        }


def _decode_image_bytes(image_bytes: bytes) -> bytes:
    if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
        raise FaceRecError("face_image_invalid", "Face matching needs non-empty image bytes (JPEG/PNG).")
    if len(image_bytes) > 10 * 1024 * 1024:
        raise FaceRecError("face_image_too_large", "Face image exceeds the 10 MB limit.")
    return bytes(image_bytes)


def _default_face_model_paths() -> tuple:
    """Resolve the embedding + landmark model files.

    Order: ``CUELIEZ_FACE_MODEL_PATH`` / ``CUELIEZ_FACE_LANDMARK_MODEL_PATH``
    env vars first (deployments supply their own copies), then the
    OpenFace models vendored with the repo's face fixtures
    (``tests/fixtures/face/models/`` -- the same public model files,
    usable as a demo fallback). Returns ``(model_path, landmark_path)``
    with ``None`` for any file that does not exist.
    """
    import os

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    fixture_dir = os.path.join(repo_root, "tests", "fixtures", "face", "models")
    model = os.environ.get(FACE_MODEL_ENV) or os.path.join(fixture_dir, "nn4.small2.v1.t7")
    landmark = os.environ.get(FACE_LANDMARK_ENV) or os.path.join(fixture_dir, "lbfmodel.yaml")
    return (
        model if model and os.path.exists(model) else None,
        landmark if landmark and os.path.exists(landmark) else None,
    )


def available_face_rec_backends() -> List[str]:
    """Backends usable in this environment (no install attempted)."""
    try:
        from .observations.face_recognition import face_available

        if face_available():
            return ["openface/nn4.small2.v1.t7 (opencv-contrib)"]
    except Exception:
        pass
    return []


class LiveFaceStore:
    """Session-scoped face matching for the live AV surface.

    Thin delegate over Track B's
    :class:`cueliez.observations.face_recognition.FaceRecognizer`:
    enrollment + embedding-distance matching happen there; this class
    adds image-bytes decoding, session scope, and a ``describe()`` for
    the sealed package. Templates are numeric embeddings held in
    memory by the recognizer, transmitted nowhere, and deleted by
    :meth:`clear` (called automatically when the owning
    :class:`LiveSession` stops). Disk persistence is a separate,
    explicit opt-in through Track B's ``FaceTemplateStore.save`` with
    a consent record; this class never writes templates to disk.
    """

    backend = "openface/nn4.small2.v1.t7 (opencv-contrib)"
    model_id = "openface/nn4.small2.v1.t7"

    def __init__(self, recognizer=None, *, model_path=None, landmark_model_path=None, match_threshold=None):
        if recognizer is not None:
            self.recognizer = recognizer
        else:
            try:
                from .observations.face_recognition import FaceRecognizer, face_available
            except Exception as exc:
                raise FaceRecError(
                    "face_rec_extra_missing",
                    "Face matching needs the optional 'face' extra: pip install 'cueliez[face]' "
                    "(opencv-contrib-python-headless==4.10.0.84). Core CueLiez stays stdlib-only; "
                    "no match score is produced without it.",
                ) from exc
            if not face_available():
                raise FaceRecError(
                    "face_rec_extra_missing",
                    "Face matching needs the optional 'face' extra: pip install 'cueliez[face]' "
                    "(opencv-contrib-python-headless==4.10.0.84). OpenCV 5.x removed the Torch "
                    "model importer, so 4.10 is pinned. No match score is produced without it.",
                )
            model, landmark = model_path, landmark_model_path
            if model is None or landmark is None:
                default_model, default_landmark = _default_face_model_paths()
                model = model or default_model
                landmark = landmark or default_landmark
            if not model:
                raise FaceRecError(
                    "face_model_missing",
                    "Face embedding model nn4.small2.v1.t7 was not found. Set CUELIEZ_FACE_MODEL_PATH "
                    "to a local copy, or use the copy vendored at tests/fixtures/face/models/.",
                )
            kwargs: Dict[str, Any] = {}
            if match_threshold is not None:
                kwargs["match_threshold"] = float(match_threshold)
            try:
                self.recognizer = FaceRecognizer(model, landmark, **kwargs)
            except Exception as exc:
                raise FaceRecError("face_model_missing", f"Face recognizer could not start: {exc}") from exc
        self.distance_threshold = float(getattr(self.recognizer, "match_threshold", 0.9))

    def _decode(self, image_bytes: bytes):
        import cv2
        import numpy as np

        data = np.frombuffer(_decode_image_bytes(image_bytes), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            raise FaceRecError("face_image_invalid", "Image bytes could not be decoded (JPEG/PNG expected).")
        return img

    def enroll(self, subject_id: str, image_bytes: bytes) -> Dict[str, Any]:
        who = (subject_id or "").strip()
        if not who:
            raise FaceRecError("face_subject_required", "Enrollment needs a non-empty subject label.")
        try:
            result = self.recognizer.enroll(who, self._decode(image_bytes))
        except FaceRecError:
            raise
        except Exception as exc:
            err = str(exc)
            if "No face detected" in err:
                raise FaceRecError("face_not_found", "No face was found in the supplied image.") from exc
            raise FaceRecError("face_enroll_failed", err) from exc
        return {
            "subject_id": who, "backend": self.backend, "model_id": self.model_id,
            "model_sha256": None, "templates_for_subject": result.get("enrollment_images", 1),
            "aligned": result.get("aligned"),
            "note": "Template is a 128-d numeric embedding held in memory; no image bytes retained.",
        }

    def match(self, image_bytes: bytes) -> FaceMatchResult:
        try:
            result = self.recognizer.match(self._decode(image_bytes))
        except Exception as exc:
            err = str(exc)
            if "No face detected" in err:
                raise FaceRecError("face_not_found", "No face was found in the supplied image.") from exc
            raise FaceRecError("face_match_failed", err) from exc
        return FaceMatchResult(
            subject_id=result.subject_id,
            distance=result.distance,
            confidence=float(result.score),
            threshold=float(result.threshold),
            backend=self.backend,
            model_id=self.model_id,
            matched=bool(result.matched),
            faces_found=1,
        )

    def detect_faces(self, image_bytes: bytes) -> int:
        return len(self.recognizer.detect_faces(self._decode(image_bytes)))

    def delete_subject(self, subject_id: str) -> bool:
        store = self._template_store()
        return store.delete_subject(subject_id)

    def clear(self) -> None:
        self.recognizer.clear()

    def enrolled_subjects(self) -> List[str]:
        return self.recognizer.enrolled_subjects()

    def _template_store(self):
        from .observations.face_recognition import FaceTemplateStore

        return FaceTemplateStore(self.recognizer)

    def save_templates(self, path: str, *, consent_record: Mapping[str, Any]) -> Dict[str, Any]:
        """Explicit opt-in persistence via Track B's store (consent record required)."""
        return self._template_store().save(path, consent_record=consent_record)

    def load_templates(self, path: str) -> List[str]:
        return self._template_store().load(path)

    def describe(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "model_id": self.model_id,
            "distance_threshold": self.distance_threshold,
            "enrolled_subjects": self.enrolled_subjects(),
            "retention": "in-memory only by default; deleted on session stop unless the operator explicitly persists with face-recognition consent recorded",
        }


def get_face_recognizer(prefer: str = "auto"):
    """Return the live-surface face store, or raise naming the missing extra.

    The live surface's recognizer IS Track B's observer
    (``cueliez.observations.face_recognition``); this factory only
    constructs it with resolved model paths. With the ``face`` extra
    missing (or the model files absent) this raises ``FaceRecError``
    with the install hint -- it never returns a fake recognizer.
    ``prefer`` accepts ``"auto"`` / ``"openface"``; anything else raises
    ``FaceRecError`` explaining that the dlib/LBPH paths were evaluated
    and set aside in favour of Track B's observer.
    """
    want = (prefer or "auto").strip().lower()
    if want not in ("auto", "openface"):
        raise FaceRecError(
            "face_rec_backend_unsupported",
            f"Face backend {prefer!r} is not used on the live surface: enrollment + matching "
            "delegate to Track B's OpenFace observer (cueliez[face]). The dlib and LBPH "
            "paths were evaluated and set aside; see live_av module notes.",
        )
    return LiveFaceStore()


# Backwards-compatible alias: the live-surface store used to be named
# FaceTemplateStore here; Track B owns that name now.
FaceTemplateStore = LiveFaceStore


# ---------------------------------------------------------------------------
# Cue wording (product templates, section 4.2)
# ---------------------------------------------------------------------------

def format_timing_cue(obs: Mapping[str, Any], *, turn_index: Optional[int] = None) -> Optional[Dict[str, str]]:
    """Reword a timing observation into the fixed product template + caveat.

    Returns ``{"message": ..., "caveat": ...}`` or None when the label is
    not a timing label. Wording is baseline-relative only; no cause or
    state of mind is named.
    """
    label = str(obs.get("label") or "")
    ev = obs.get("evidence") or {}
    if label == "response_latency_anomaly_observed":
        value_ms = float(ev.get("latency_ms") or 0.0)
        base_ms = float(ev.get("baseline_median_ms") or 0.0)
        direction = str(ev.get("direction") or ("longer" if value_ms > base_ms else "shorter"))
        if direction not in ("longer", "shorter"):
            direction = "longer" if value_ms > base_ms else "shorter"
        msg = (
            f"Response delay was {direction} than earlier in this interview "
            f"({_fmt_seconds(value_ms)} s against about {_fmt_seconds(base_ms)} s), "
            f"around {_fmt_mmss(ev.get('t_media_ms'))}."
        )
    elif label == "speech_rate_shift_observed":
        wpm = float(ev.get("wpm") or 0.0)
        base = float(ev.get("baseline_median_wpm") or 0.0)
        direction = str(ev.get("direction") or "")
        word = "higher" if direction in ("faster", "higher") else "lower" if direction in ("slower", "lower") else ("higher" if wpm > base else "lower")
        start = _fmt_mmss(ev.get("t_start_ms"))
        end = _fmt_mmss(ev.get("t_end_ms"))
        msg = (
            f"Speech rate was {word} than earlier in this interview "
            f"({wpm:.0f} against about {base:.0f} words per minute) between {start} and {end}."
        )
    elif label == "pause_duration_elevated_observed":
        start = _fmt_mmss(ev.get("t_start_ms"))
        end = _fmt_mmss(ev.get("t_end_ms"))
        msg = (
            "Pauses within answers were more frequent than earlier in this interview "
            f"between {start} and {end}."
        )
    else:
        return None
    caveat = TIMING_CAVEATS[label]
    _check_live_text(msg)
    return {"message": msg, "caveat": caveat}


def format_video_cue(label: str, *, direction: str, t_start_ms: float, t_end_ms: float) -> Optional[Dict[str, str]]:
    """Format a video-window cue from the fixed product templates."""
    start, end = _fmt_mmss(t_start_ms), _fmt_mmss(t_end_ms)
    if label == "gaze_pattern_shift_observed":
        word = "more" if direction == "higher" else "less"
        msg = f"Gaze was directed away from the camera {word} often than earlier in this interview between {start} and {end}."
    elif label == "blink_rate_shift_observed":
        word = "higher" if direction == "higher" else "lower"
        msg = f"Blink rate was {word} than earlier in this interview between {start} and {end}."
    elif label == "motor_activity_shift_observed":
        word = "higher" if direction == "higher" else "lower"
        msg = f"Overall movement was {word} than earlier in this interview between {start} and {end}."
    else:
        return None
    caveat = VIDEO_CAVEATS[label]
    _check_live_text(msg)
    return {"message": msg, "caveat": caveat}


def _baseline_shift(values: Sequence[float]) -> Optional[Dict[str, Any]]:
    """Median/MAD baseline shift for a windowed series (same math as the observers).

    Needs at least 3 values; fires at |robust z| >= 2.0. Returns None
    when there is no shift or not enough data.
    """
    vals = [float(v) for v in values]
    if len(vals) < 3:
        return None
    med = statistics.median(vals)
    mad = statistics.median([abs(v - med) for v in vals]) or 1e-9
    last = vals[-1]
    z = (last - med) / (1.4826 * mad)
    if abs(z) < 2.0:
        return None
    return {"direction": "higher" if z > 0 else "lower", "median": med, "robust_z": round(z, 3), "value": last}


# ---------------------------------------------------------------------------
# Live session
# ---------------------------------------------------------------------------

class _CaptureSource:
    """Minimal capture-source contract: open() only after the gate passes."""

    def __init__(self, name: str = "capture"):
        self.name = name
        self.open_count = 0
        self.close_count = 0
        self.opened = False

    def open(self) -> None:
        self.open_count += 1
        self.opened = True

    def close(self) -> None:
        self.close_count += 1
        self.opened = False


class LiveSession:
    """One officer-run live audio/video session.

    Owns the gate checks, the modality state + timeline, the finalised
    turn pipeline (reusing the existing stream runner), the timing and
    video cue paths, and the sealed-package ``live_inputs`` block.
    Capture devices are opened only after the gate passes; the kill
    switch (``stop``) closes them at once and discards in-flight data.
    """

    def __init__(
        self,
        state: SessionGateState,
        *,
        session_id: Optional[str] = None,
        stt_adapter: Any = None,
        consent_text_version: str = CONSENT_TEXT_VERSION,
        baseline_window_s: float = 120.0,
        baseline_min_turns: int = 3,
        capture_source: Any = None,
        video_capture_source: Any = None,
    ):
        if not isinstance(state, SessionGateState):
            raise GateError("gate_state_required", "LiveSession needs a SessionGateState.")
        self.state = state
        self.session_id = session_id or f"live-{secrets.token_hex(6)}"
        self.stt_adapter = stt_adapter or BrowserSttAdapter()
        self.cloud_stt = CloudSttAdapter()
        self.consent_text_version = consent_text_version
        self.baseline_window_s = float(baseline_window_s)
        self.baseline_min_turns = int(baseline_min_turns)
        self.ingest_token = secrets.token_urlsafe(24)
        self._t0_mono = time.monotonic()
        self._started_wall: Optional[float] = None
        self._status: Dict[str, str] = {"audio_capture": "OFF", "audio_features": "OFF", "camera": "OFF", "face_recognition": "OFF"}
        self._capture_source = capture_source
        self._video_capture_source = video_capture_source
        self._segment_id = 0
        self.timeline: List[Dict[str, Any]] = []
        self.transcript: List[Dict[str, Any]] = []
        self.observations: List[Dict[str, Any]] = []
        self.cues_shown: List[Dict[str, Any]] = []
        self.video_windows: List[Dict[str, Any]] = []
        self._seen_cue_ids: set = set()
        self._seen_chunk_seqs: set = set()
        self._expected_seq = 0
        self.counters: Dict[str, Any] = {
            "chunks_received": 0, "chunks_duplicate": 0, "chunks_gap": 0,
            "gap_filled_ms": 0, "dropped_ms": 0, "stalls": 0,
            "turns_received": 0, "turns_unconfirmed": 0, "turns_rejected_raw_media": 0,
            "face_enrollments": 0, "face_matches": 0, "face_match_hits": 0,
        }
        self._open_turn: Optional[Dict[str, Any]] = None
        self._face_store: Optional[FaceTemplateStore] = None
        self._sse_events: List[Dict[str, Any]] = []
        self._sse_next_id = 0
        self._lock = threading.Lock()

    # -- clocks / timeline -------------------------------------------------
    def media_ms(self) -> float:
        return (time.monotonic() - self._t0_mono) * 1000.0

    def _event(self, *, event: str, modality: str, reason: str = "", code: str = "") -> Dict[str, Any]:
        rec = {
            "event": event, "modality": modality, "reason": reason, "code": code,
            "t_media_ms": round(self.media_ms(), 1), "t_wall": time.time(),
            "segment_id": self._segment_id,
        }
        self.timeline.append(rec)
        self._push_sse("state", {"event": event, "modality": modality, "reason": reason})
        return rec

    def _push_sse(self, kind: str, payload: Dict[str, Any]) -> None:
        self._sse_next_id += 1
        self._sse_events.append({"id": self._sse_next_id, "kind": kind, "data": payload})

    def events_since(self, last_id: int) -> List[Dict[str, Any]]:
        return [e for e in self._sse_events if e["id"] > int(last_id)]

    @property
    def live_inputs_timeline(self) -> List[Dict[str, Any]]:
        return list(self.timeline)

    # -- start / stop ------------------------------------------------------
    def _check_start(self, modality: str) -> None:
        _require_live_mode(self.state)
        require_live_modality(self.state, modality)

    def start(self, modality: str, *, capture_source: Any = None) -> Dict[str, Any]:
        """Start one modality after its gate passes. The capture source
        is opened only after the checks succeed (refusal => zero opens)."""
        key = _normalize_modality(modality)
        if key not in ("audio_capture", "camera", "face_recognition"):
            raise GateError("modality_invalid", f"Live start supports audio_capture, camera, face_recognition; got {modality!r}.")
        if key == "face_recognition":
            return self.enable_face_recognition()
        self._check_start(key)
        source = capture_source or (self._capture_source if key == "audio_capture" else self._video_capture_source)
        if self._status[key] == "ON":
            return self.status()
        if source is not None and hasattr(source, "open"):
            source.open()
        if self._started_wall is None:
            self._started_wall = time.time()
        self._status[key] = "ON"
        if key == "audio_capture":
            self._segment_id += 1
        self._event(event="start", modality=key, reason="officer_start")
        return self.status()

    def start_audio(self, *, capture_source: Any = None) -> Dict[str, Any]:
        return self.start("audio_capture", capture_source=capture_source)

    def start_video(self, *, capture_source: Any = None) -> Dict[str, Any]:
        return self.start("camera", capture_source=capture_source)

    def enable_face_recognition(self, *, recognizer: Any = None) -> Dict[str, Any]:
        """Enable real face matching behind face-recognition consent."""
        self._check_start("face_recognition")
        if self._face_store is None:
            if recognizer is None:
                self._face_store = get_face_recognizer()
            elif isinstance(recognizer, LiveFaceStore):
                self._face_store = recognizer
            else:
                # A Track B FaceRecognizer passed directly.
                self._face_store = LiveFaceStore(recognizer)
        if self._status["face_recognition"] != "ON":
            self._status["face_recognition"] = "ON"
            self._event(event="start", modality="face_recognition", reason="officer_start")
        return self.status()

    def stop(self, reason: str = "officer_stop", *, modalities: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        """Kill switch: stop all (or the listed) live inputs at once.

        Capture stops, in-flight buffers and any open turn are discarded
        (not finalised), no further cue is produced from stopped inputs,
        and the event is recorded. The session can still seal afterwards.
        A stop is a human action; it does not end the interview.
        """
        keys = [_normalize_modality(m) for m in modalities] if modalities else ["audio_capture", "audio_features", "camera", "face_recognition"]
        for key in keys:
            if key == "audio_features":
                # Timing is a switch on the audio path, not a device.
                self._status["audio_features"] = "OFF"
                self._event(event="stop", modality="audio_features", reason=reason)
                continue
            if self._status.get(key) == "ON":
                self._status[key] = "STOPPED BY OFFICER" if reason == "officer_stop" else "DOWN"
                self._event(event="stop", modality=key, reason=reason, code=reason)
        for source in (self._capture_source, self._video_capture_source):
            if source is not None and hasattr(source, "close"):
                try:
                    source.close()
                except Exception:
                    pass
        self._open_turn = None
        if self._face_store is not None and "face_recognition" in keys:
            # Templates are session-scoped by default: stopping face
            # matching deletes them. Re-enrollment is needed to restart.
            self._face_store.clear()
            self._face_store = None
        return self.status()

    def kill_switch(self, reason: str = "officer_stop") -> Dict[str, Any]:
        return self.stop(reason=reason)

    def stop_modality(self, modality: str, reason: str = "officer_stop") -> Dict[str, Any]:
        return self.stop(reason=reason, modalities=[modality])

    def set_timing_enabled(self, enabled: bool) -> Dict[str, Any]:
        """Switch the separately-consented timing indicators on/off live."""
        if enabled:
            require_live_modality(self.state, "audio_features")
            if self._status.get("audio_capture") != "ON":
                raise GateError("live_input_not_running", "Audio timing needs a running audio capture first.")
            self._status["audio_features"] = "ON"
            self._event(event="start", modality="audio_features", reason="officer_start")
        else:
            self._status["audio_features"] = "OFF"
            self._event(event="stop", modality="audio_features", reason="officer_stop")
        return self.status()

    def status(self) -> Dict[str, Any]:
        elapsed = None
        if self._started_wall is not None:
            elapsed = round(time.time() - self._started_wall, 1)
        return {
            "session_id": self.session_id,
            "modalities": dict(self._status),
            "elapsed_s": elapsed,
            "baseline_ready": self.baseline_ready,
            "baseline_state": "ready" if self.baseline_ready else "Not enough baseline yet",
            "subject_not_shown": True,
            "notice": "Officer-only view. The subject is not shown this stream.",
        }

    @property
    def baseline_ready(self) -> bool:
        subject_turns = [t for t in self.transcript if is_subject_turn(t)]
        if len(subject_turns) < self.baseline_min_turns:
            return False
        return self.media_ms() >= self.baseline_window_s * 1000.0

    # -- audio ingest ------------------------------------------------------
    def ingest_audio_chunk(self, seq: int, n_bytes: int) -> Dict[str, Any]:
        """Ingest one numbered audio chunk (100 ms PCM). Idempotent on
        duplicate seq; gaps are counted and recorded, never silently repaired."""
        if self._status.get("audio_capture") != "ON":
            raise GateError("live_input_not_running", "Audio capture is not running; chunk rejected.")
        self.counters["chunks_received"] += 1
        if seq in self._seen_chunk_seqs:
            self.counters["chunks_duplicate"] += 1
            return {"ack": seq, "dup": True}
        if seq != self._expected_seq:
            gap = seq - self._expected_seq
            self.counters["chunks_gap"] += 1
            self.counters["gap_filled_ms"] += max(0, gap) * 100
            self._event(event="gap", modality="audio_capture", reason="chunk_gap", code=f"expected_seq_{self._expected_seq}")
        self._seen_chunk_seqs.add(seq)
        self._expected_seq = max(self._expected_seq, seq + 1)
        return {"ack": seq}

    def ingest_final_turn(self, turn: Mapping[str, Any], *, source: str = "browser-stt") -> Dict[str, Any]:
        """Accept one finalised turn (browser STT, typed fallback, or a
        local adapter) and run it through the existing stream pipeline.

        Partials are never accepted here (the capture page shows them as
        captions only). A turn whose speaker cannot be established is
        kept in the transcript as ``speaker_unconfirmed`` and is never a
        cue source. Raw media keys are rejected outright.
        """
        if self._status.get("audio_capture") != "ON":
            raise GateError("live_input_not_running", "Audio capture is not running; turn rejected.")
        if not isinstance(turn, Mapping):
            raise ValueError("turn must be a JSON object")
        bad = set(turn) & RAW_MEDIA_KEYS
        if bad:
            self.counters["turns_rejected_raw_media"] += 1
            raise ValueError(f"turn carries raw media fields and was rejected: {sorted(bad)}")
        text = str(turn.get("text") or "").strip()
        if not text:
            raise ValueError("finalised turn needs non-empty text")
        stored = dict(turn)
        stored.setdefault("source", source)
        stored.setdefault("t_media_ms", round(self.media_ms(), 1))
        stored.setdefault("stt_component", self.stt_adapter.describe())
        role = str(stored.get("role") or "").strip().lower()
        if role not in ("subject", "officer", "interviewee", "interviewer"):
            stored["role"] = "speaker_unconfirmed"
            stored["speaker_unconfirmed"] = True
        self.transcript.append(stored)
        self.counters["turns_received"] += 1
        out: Dict[str, Any] = {"turn_index": len(self.transcript) - 1, "cues": []}
        if stored.get("speaker_unconfirmed"):
            self.counters["turns_unconfirmed"] += 1
            self._push_sse("turn", {"turn_index": out["turn_index"], "speaker_unconfirmed": True})
            return out
        new_cues = self._run_pipeline_for_turn(len(self.transcript) - 1)
        out["cues"] = new_cues
        return out

    def _run_pipeline_for_turn(self, turn_index: int) -> List[Dict[str, Any]]:
        """Reuse the existing stream runner; timing is a separate switch."""
        runner = default_runner()
        observations = runner.run(self.transcript)
        timing_on = self._status.get("audio_features") == "ON"
        # Timing labels survive only when the separate timing switch is on
        # AND the baseline is complete (product scope A1-2). Before the
        # baseline completes the officer sees "Not enough baseline yet",
        # never a shift cue -- even though the text runner also carries
        # latency / speech-rate observers.
        if timing_on and self.baseline_ready:
            timing_obs = observe_live_audio_timing(self.transcript, state=self.state, require_consent_check=True)
            seen_labels = {(o.get("label"), o.get("turn_index")) for o in observations}
            for o in timing_obs:
                if (o.get("label"), o.get("turn_index")) not in seen_labels:
                    observations.append(o)
        else:
            observations = [o for o in observations if o.get("label") not in TIMING_LABELS]
        observations = [o for o in observations if o.get("label") not in PROSODY_LABELS and o.get("label") not in VISUAL_LABELS]
        new: List[Dict[str, Any]] = []
        for obs in observations:
            cid = obs.get("cue_id")
            if cid and cid in self._seen_cue_ids:
                continue
            if cid:
                self._seen_cue_ids.add(cid)
            label = str(obs.get("label") or "")
            if label in TIMING_LABELS:
                # Enrich the evidence with the turn's media-time window so
                # the template's "between {start} and {end}" / "around {time}"
                # slots carry real times, not placeholders.
                turn = self.transcript[obs.get("turn_index")] if isinstance(obs.get("turn_index"), int) and 0 <= obs["turn_index"] < len(self.transcript) else {}
                t_end = float(turn.get("t_media_ms") or 0.0)
                dur = float(turn.get("duration_ms") or 0.0)
                ev = dict(obs.get("evidence") or {})
                ev.setdefault("t_media_ms", t_end)
                ev.setdefault("t_start_ms", max(0.0, t_end - dur))
                ev.setdefault("t_end_ms", t_end)
                obs = dict(obs, evidence=ev)
            cue_text = obs.get("cue") or label.replace("_", " ")
            source_tag, priority, caveat = "text", None, None
            if label in TIMING_LABELS:
                formatted = format_timing_cue(obs)
                if formatted is None:
                    continue
                cue_text, caveat = formatted["message"], formatted["caveat"]
                source_tag, priority = "audio timing", "medium"
                # The sealed observation carries the same template wording
                # + caveat as the cue shown to the officer.
                obs = dict(obs, cue=cue_text + " " + caveat)
            self.observations.append(obs)
            cue = {
                "cue_id": cid, "label": label, "category": obs.get("category"),
                "message": cue_text, "score": (obs.get("confidence") or {}).get("score"),
                "turn_index": obs.get("turn_index"), "source": source_tag,
                "priority": priority, "caveat": caveat,
            }
            new.append(cue)
            self.cues_shown.append(cue)
        if new:
            self._push_sse("cue", {"cues": new})
        return new

    # -- video ingest ------------------------------------------------------
    def ingest_video_window(self, window: Any) -> Dict[str, Any]:
        """Accept one derived-feature window (aggregates only). Frames are
        never accepted, stored, or transmitted by this path; a window
        carrying frame-ish fields is rejected."""
        if self._status.get("camera") != "ON":
            raise GateError("live_input_not_running", "Video capture is not running; window rejected.")
        win = window if isinstance(window, VideoWindow) else VideoWindow.from_dict(window)
        self.video_windows.append(win.to_dict())
        out: Dict[str, Any] = {"window": win.to_dict(), "cues": [], "state": "ok"}
        if win.tracking_quality < 0.5 and (win.off_camera_gaze_share is not None or win.blink_count is not None):
            out["state"] = "Tracking quality too low"
            return out
        cues: List[Dict[str, Any]] = []
        windows = self.video_windows
        if len(windows) >= 3:
            gaze_series = [w["off_camera_gaze_share"] for w in windows if w.get("off_camera_gaze_share") is not None]
            if len(gaze_series) >= 3:
                turn_like = [
                    {"role": "subject", "text": "", "off_camera_gaze_share": w["off_camera_gaze_share"],
                     "t_start_ms": w["t_start_ms"], "t_end_ms": w["t_end_ms"]}
                    for w in windows if w.get("off_camera_gaze_share") is not None
                ]
                for obs in GazePatternObserver().observe(turn_like).to_dicts():
                    formatted = format_video_cue(
                        "gaze_pattern_shift_observed",
                        direction=str((obs.get("evidence") or {}).get("direction") or "higher"),
                        t_start_ms=float(win.t_start_ms), t_end_ms=float(win.t_end_ms),
                    )
                    if formatted is None:
                        continue
                    if obs.get("cue_id") not in self._seen_cue_ids:
                        self.observations.append(dict(obs, cue=formatted["message"] + " " + formatted["caveat"]))
                    cues.append(self._video_cue(obs, formatted, win))
            blink_series = [w["blink_count"] for w in windows if w.get("blink_count") is not None]
            if len(blink_series) >= 3:
                rates = []
                for w in windows:
                    if w.get("blink_count") is None:
                        continue
                    dur_min = max(1.0, (float(w["t_end_ms"]) - float(w["t_start_ms"]))) / 60000.0
                    rates.append(w["blink_count"] / dur_min)
                turn_like = [
                    {"role": "subject", "text": "", "blink_rate_per_min": r}
                    for r in rates
                ]
                for obs in BlinkRateObserver().observe(turn_like).to_dicts():
                    formatted = format_video_cue(
                        "blink_rate_shift_observed",
                        direction=str((obs.get("evidence") or {}).get("direction") or "higher"),
                        t_start_ms=float(win.t_start_ms), t_end_ms=float(win.t_end_ms),
                    )
                    if formatted is None:
                        continue
                    if obs.get("cue_id") not in self._seen_cue_ids:
                        self.observations.append(dict(obs, cue=formatted["message"] + " " + formatted["caveat"]))
                    cues.append(self._video_cue(obs, formatted, win))
            movement_series = [w["movement_index"] for w in windows if w.get("movement_index") is not None]
            shift = _baseline_shift(movement_series)
            if shift is not None:
                formatted = format_video_cue(
                    "motor_activity_shift_observed", direction=shift["direction"],
                    t_start_ms=float(win.t_start_ms), t_end_ms=float(win.t_end_ms),
                )
                if formatted is not None:
                    obs = {
                        "label": "motor_activity_shift_observed", "confidence": {"score": 0.4, "model_id": "cueliez.live_av.movement/v1"},
                        "category": "visual", "method": "cueliez.live_av.movement/v1",
                        "evidence": {"movement_index": shift["value"], "median": shift["median"], "robust_z": shift["robust_z"], "direction": shift["direction"]},
                        "cue_id": f"live-video-movement-{len(windows)}", "turn_index": None,
                    }
                    if obs.get("cue_id") not in self._seen_cue_ids:
                        self.observations.append(dict(obs, cue=formatted["message"] + " " + formatted["caveat"]))
                    cues.append(self._video_cue(obs, formatted, win))
        new_cues: List[Dict[str, Any]] = []
        for cue in cues:
            if cue["cue_id"] in self._seen_cue_ids:
                continue
            self._seen_cue_ids.add(cue["cue_id"])
            self.cues_shown.append(cue)
            new_cues.append(cue)
        out["cues"] = new_cues
        if out["cues"]:
            self._push_sse("cue", {"cues": out["cues"]})
        return out

    def _video_cue(self, obs: Mapping[str, Any], formatted: Dict[str, str], win: VideoWindow) -> Dict[str, Any]:
        # Video cues are capped at the lowest priority tier and never
        # raise a high-priority cue or a dual-control trigger.
        return {
            "cue_id": obs.get("cue_id") or f"live-video-{obs.get('label')}-{len(self.video_windows)}",
            "label": obs.get("label"), "category": "visual",
            "message": formatted["message"], "score": (obs.get("confidence") or {}).get("score"),
            "turn_index": None, "source": "video-derived",
            "priority": "low", "caveat": formatted["caveat"],
            "window": {"t_start_ms": win.t_start_ms, "t_end_ms": win.t_end_ms,
                       "tracking_quality": round(win.tracking_quality, 4)},
        }

    # -- face matching -----------------------------------------------------
    def enroll_face(self, subject_id: str, image_bytes: bytes) -> Dict[str, Any]:
        if self._status.get("face_recognition") != "ON" or self._face_store is None:
            raise GateError("live_input_not_running", "Face matching is not running; enroll refused.")
        result = self._face_store.enroll(subject_id, image_bytes)
        self.counters["face_enrollments"] += 1
        self._event(event="face_enroll", modality="face_recognition", reason=f"enrolled:{subject_id}")
        return result

    def match_face(self, image_bytes: bytes) -> Dict[str, Any]:
        if self._status.get("face_recognition") != "ON" or self._face_store is None:
            raise GateError("live_input_not_running", "Face matching is not running; match refused.")
        result = self._face_store.match(image_bytes)
        self.counters["face_matches"] += 1
        if result.matched:
            self.counters["face_match_hits"] += 1
        self._event(event="face_match", modality="face_recognition",
                    reason="matched" if result.matched else "no_match")
        return result.to_dict()

    # -- sealed package ----------------------------------------------------
    def build_live_inputs_block(self) -> Dict[str, Any]:
        stt_info: Dict[str, Any] = {}
        try:
            stt_info = self.stt_adapter.describe()
        except Exception as exc:  # adapter unavailable: record that honestly
            stt_info = {"component_id": getattr(self.stt_adapter, "component_id", "unknown"), "error": str(exc)}
        try:
            cloud_info = self.cloud_stt.describe()
        except CloudSttNotConfigured:
            cloud_info = {"configured": False, "note": "Cloud transcription is not configured; no provider is bundled."}
        block: Dict[str, Any] = {
            "live_av_version": LIVE_AV_VERSION,
            "session_id": self.session_id,
            "consent_text_version": self.consent_text_version,
            "live_training_version": LIVE_TRAINING_VERSION,
            "modality_consents": {
                k: dict(v) for k, v in (self.state.modality_consents or {}).items()
                if k in LIVE_MODALITY_KEYS
            },
            "modality_states": dict(self._status),
            "timeline": list(self.timeline),
            "live_inputs_timeline": list(self.timeline),
            "capture_config": {
                "sample_rate": 16000, "channels": 1, "chunk_ms": 100,
                "browser_constraints": {"echoCancellation": False, "autoGainControl": False, "noiseSuppression": False},
                "turn_end_hold_ms": 800, "video_window_ms": 30000,
            },
            "components": {
                "speech_to_text": stt_info,
                "cloud_transcription": cloud_info,
                "face_matching": self._face_store.describe() if self._face_store is not None else {"enabled": False},
            },
            "quality_counters": dict(self.counters),
            "live_cues_shown": list(self.cues_shown),
            "video_windows": list(self.video_windows),
            "turns_unconfirmed_count": self.counters["turns_unconfirmed"],
            "notes": [
                "Raw audio and video frames are processed in memory only and are never stored by CueLiez.",
                "Video-derived and audio-timing cues are baseline-relative observations for officer review.",
                "Phase B production use requires the entry gate: counsel answers, literature review, and an over-cue report reviewed by the owner.",
            ],
        }
        return block

    def seal_package(self, package: Optional[Dict[str, Any]] = None, *, signer: Any = None) -> Dict[str, Any]:
        """Attach the live_inputs block (inside the hashed area) and seal
        through the existing gate-hardened seal path."""
        pkg: Dict[str, Any] = dict(package) if package is not None else {}
        pkg.setdefault("observations", list(self.observations))
        pkg.setdefault("annotations", {"mode": self.state.mode, "live_av": True})
        pkg["live_inputs"] = self.build_live_inputs_block()
        return _seal_package(pkg, self.state, signer=signer)

    def close(self) -> None:
        """Stop everything and delete in-memory face templates."""
        try:
            self.stop(reason="session_close")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# HTTP server + officer capture page (stdlib only)
# ---------------------------------------------------------------------------

_CAPTURE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CueLiez Live AV — Officer Capture (observation cues only)</title>
<style>
body { font-family: system-ui, sans-serif; margin: 1rem; background:#0b0f14; color:#e6edf3; }
h1 { font-size:1.1rem; }
.notice { background:#1f2937; padding:.75rem; border-radius:.5rem; margin-bottom:1rem; font-size:.9rem; }
.strip { display:flex; gap:.5rem; flex-wrap:wrap; margin-bottom:1rem; }
.pill { border:1px solid #374151; border-radius:999px; padding:.3rem .7rem; font-size:.85rem; }
.on { border-color:#34d399; color:#34d399; } .off { color:#9ca3af; } .stopped { border-color:#f87171; color:#f87171; }
button { margin:.2rem; padding:.5rem .8rem; border-radius:.4rem; border:1px solid #374151; background:#1f2937; color:#e6edf3; cursor:pointer; }
button.kill { border-color:#f87171; color:#f87171; font-weight:700; }
.cue { border:1px solid #374151; border-radius:.5rem; padding:.75rem; margin:.5rem 0; }
.meta { color:#9ca3af; font-size:.8rem; }
.src { color:#93c5fd; font-size:.8rem; margin-top:.25rem; }
.caption { color:#9ca3af; font-style:italic; }
video { width:320px; max-width:100%; border:1px solid #374151; border-radius:.5rem; background:#000; }
textarea, select, input { background:#111827; color:#e6edf3; border:1px solid #374151; border-radius:.4rem; padding:.4rem; }
section { margin-bottom:1.2rem; }
</style>
</head>
<body>
<h1>CueLiez — Live AV Capture (officer only)</h1>
<div class="notice">Officer-only view. The subject is not shown this stream. Cues are probabilistic observations for professional review — not findings. Machine transcript text may contain errors. Raw audio and video frames are processed in memory only and are never stored by CueLiez.</div>
<div class="strip" id="strip"></div>
<div>
<button id="btnAudio">Start audio (mic + speech-to-text)</button>
<button id="btnTiming">Enable audio timing</button>
<button id="btnVideo">Start video (derived features)</button>
<button id="btnFace">Enable face matching</button>
<button id="btnKill" class="kill">KILL SWITCH — stop all live inputs (K)</button>
</div>
<section>
<h2>Camera preview (officer only)</h2>
<video id="preview" muted playsinline></video>
<div class="meta" id="videoState">Video not started. Gaze and blink are not computed in this page: no face model is bundled. Movement is computed in-page by frame differencing.</div>
</section>
<section>
<h2>Machine transcript (finalised turns)</h2>
<div id="captions" class="caption">No captions yet.</div>
<div id="turns"></div>
</section>
<section>
<h2>Cues</h2>
<div id="cues"><p class="caption">No cues yet.</p></div>
</section>
<section>
<h2>Typed / pasted turn (fallback when speech recognition is unavailable)</h2>
<select id="typedRole"><option value="subject">subject</option><option value="officer">officer</option></select>
<textarea id="typedText" rows="2" cols="60" placeholder="Type or paste a finalised turn"></textarea>
<button id="btnTyped">Submit typed turn</button>
</section>
<section>
<h2>Face matching (gated: face-recognition consent + jurisdiction required)</h2>
<input id="faceSubject" placeholder="subject label for enrollment">
<button id="btnEnroll">Enroll from camera</button>
<button id="btnMatch">Match from camera</button>
<div class="meta" id="faceResult">Face matching is off until enabled. Templates are numeric vectors held in memory on this host; stills sent for matching are decoded in memory and discarded, never stored.</div>
</section>
<script>
const params = new URLSearchParams(location.search);
const TOKEN = params.get('token') || '';
const SID = params.get('session') || '';
const base = '/live/v1/' + encodeURIComponent(SID);
function headers() { return {'Content-Type': 'application/json', 'X-Ingest-Token': TOKEN}; }
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
async function post(path, body) {
  const r = await fetch(base + path, {method: 'POST', headers: headers(), body: JSON.stringify(body || {})});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((data && data.error) || ('request failed: ' + r.status));
  return data;
}
async function refresh() {
  try {
    const r = await fetch(base + '/state?token=' + encodeURIComponent(TOKEN));
    const data = await r.json();
    const strip = document.getElementById('strip');
    strip.replaceChildren();
    const mods = (data && data.modalities) || {};
    for (const [k, v] of Object.entries(mods)) {
      const pill = el('span', 'pill ' + (v === 'ON' ? 'on' : (v === 'OFF' ? 'off' : 'stopped')), k + ': ' + v);
      strip.append(pill);
    }
    if (data && data.elapsed_s != null) strip.append(el('span', 'pill', 'elapsed: ' + data.elapsed_s + 's'));
    if (data && data.baseline_state) strip.append(el('span', 'pill', 'baseline: ' + data.baseline_state));
    const cues = (data && data.cues_shown) || [];
    const box = document.getElementById('cues');
    box.replaceChildren();
    if (!cues.length) { box.append(el('p', 'caption', 'No cues yet.')); }
    for (const c of cues.slice(-20)) {
      const card = el('div', 'cue');
      card.append(el('div', 'meta', (c.source || '') + ' · priority ' + (c.priority || 'normal') + ' · score ' + (typeof c.score === 'number' ? c.score.toFixed(2) : '')));
      card.append(el('div', null, c.message || ''));
      if (c.caveat) card.append(el('div', 'src', c.caveat));
      box.append(card);
    }
    const turns = (data && data.turns) || [];
    const tbox = document.getElementById('turns');
    tbox.replaceChildren();
    for (const t of turns.slice(-10)) {
      tbox.append(el('div', null, (t.role || '?') + ': ' + (t.text || '')));
    }
  } catch (e) { /* keep last rendered state; polling retries */ }
}
setInterval(refresh, 1000);
refresh();
let audioStream = null, videoStream = null, recog = null, recogStart = 0, lastVideoFrame = null, moveSum = 0, moveN = 0, winStart = 0, winFrames = 0;
function stopTracks() {
  if (audioStream) { audioStream.getTracks().forEach(t => t.stop()); audioStream = null; }
  if (videoStream) { videoStream.getTracks().forEach(t => t.stop()); videoStream = null; }
  if (recog) { try { recog.stop(); } catch (e) {} recog = null; }
}
async function killAll() {
  stopTracks();
  try { await post('/stop', {reason: 'officer_stop'}); } catch (e) {}
  document.getElementById('videoState').textContent = 'Stopped by officer.';
  refresh();
}
document.getElementById('btnKill').addEventListener('click', killAll);
document.addEventListener('keydown', (e) => { if (e.key === 'k' || e.key === 'K') killAll(); });
document.getElementById('btnAudio').addEventListener('click', async () => {
  try {
    await post('/start', {modality: 'audio_capture'});
    audioStream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: false, noiseSuppression: false, autoGainControl: false}});
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { document.getElementById('captions').textContent = 'Speech recognition is not available in this browser. Use the typed-turn fallback below.'; return; }
    recog = new SR();
    recog.continuous = true; recog.interimResults = true; recog.lang = 'en-US';
    recog.onresult = async (ev) => {
      let interim = '';
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const res = ev.results[i];
        if (res.isFinal) {
          const text = res[0].transcript;
          const now = performance.now();
          const dur = Math.max(500, now - (recogStart || now));
          recogStart = now;
          try { await post('/turn', {role: document.getElementById('typedRole').value || 'subject', text: text, duration_ms: Math.round(dur), source: 'browser-speech-recognition'}); refresh(); }
          catch (e) { document.getElementById('captions').textContent = 'Turn rejected: ' + e.message; }
        } else { interim += res[0].transcript; }
      }
      if (interim) document.getElementById('captions').textContent = 'machine transcript (partial, may contain errors): ' + interim;
    };
    recog.onerror = (ev) => { document.getElementById('captions').textContent = 'Speech recognition error: ' + (ev.error || 'unknown') + '. Use the typed-turn fallback below.'; };
    recogStart = performance.now();
    recog.start();
  } catch (e) { document.getElementById('captions').textContent = 'Audio start failed: ' + e.message; }
});
document.getElementById('btnTiming').addEventListener('click', async () => {
  try { await post('/start', {modality: 'audio_features'}); refresh(); }
  catch (e) { alert('Timing could not be enabled: ' + e.message); }
});
document.getElementById('btnVideo').addEventListener('click', async () => {
  try {
    await post('/start', {modality: 'camera'});
    videoStream = await navigator.mediaDevices.getUserMedia({video: {width: 640, height: 480}});
    const v = document.getElementById('preview');
    v.srcObject = videoStream;
    await v.play();
    winStart = performance.now(); moveSum = 0; moveN = 0; winFrames = 0; lastVideoFrame = null;
    const canvas = document.createElement('canvas'); canvas.width = 160; canvas.height = 120;
    const ctx = canvas.getContext('2d', {willReadFrequently: true});
    setInterval(() => {
      if (!videoStream) return;
      ctx.drawImage(v, 0, 0, 160, 120);
      const img = ctx.getImageData(0, 0, 160, 120).data;
      if (lastVideoFrame) {
        let diff = 0;
        for (let i = 0; i < img.length; i += 4) diff += Math.abs(img[i] - lastVideoFrame[i]);
        moveSum += diff / (160 * 120); moveN++;
      }
      lastVideoFrame = new Uint8ClampedArray(img);
      winFrames++;
      if (performance.now() - winStart >= 30000) {
        const win = {t_start_ms: Math.round(winStart), t_end_ms: Math.round(performance.now()), frames_total: winFrames, frames_tracked: 0, off_camera_gaze_share: null, blink_count: null, movement_index: moveN ? +(moveSum / moveN).toFixed(4) : null};
        post('/video-window', win).catch(() => {});
        winStart = performance.now(); moveSum = 0; moveN = 0; winFrames = 0;
      }
    }, 500);
    document.getElementById('videoState').textContent = 'Video on: movement is computed in-page by frame differencing. Gaze and blink are not computed (no face model bundled); tracking quality is reported as too low for those indicators.';
  } catch (e) { document.getElementById('videoState').textContent = 'Video start failed: ' + e.message; }
});
document.getElementById('btnFace').addEventListener('click', async () => {
  try { await post('/start', {modality: 'face_recognition'}); refresh(); }
  catch (e) { alert('Face matching could not be enabled: ' + e.message); }
});
document.getElementById('btnTyped').addEventListener('click', async () => {
  const text = document.getElementById('typedText').value.trim();
  if (!text) return;
  try {
    await post('/typed-turn', {role: document.getElementById('typedRole').value || 'subject', text: text});
    document.getElementById('typedText').value = '';
    refresh();
  } catch (e) { alert('Typed turn rejected: ' + e.message); }
});
async function faceStill() {
  const v = document.getElementById('preview');
  if (!v || !v.videoWidth) throw new Error('Start video first so the camera can supply a still.');
  const canvas = document.createElement('canvas');
  canvas.width = v.videoWidth; canvas.height = v.videoHeight;
  canvas.getContext('2d').drawImage(v, 0, 0);
  return canvas.toDataURL('image/jpeg', 0.85).split(',')[1];
}
document.getElementById('btnEnroll').addEventListener('click', async () => {
  const subject = document.getElementById('faceSubject').value.trim();
  if (!subject) { alert('Enter a subject label for enrollment.'); return; }
  try {
    const image_b64 = await faceStill();
    const res = await post('/face-enroll', {subject_id: subject, image_b64: image_b64});
    document.getElementById('faceResult').textContent = 'Enrolled ' + subject + ' (' + (res.backend || '') + '; templates for subject: ' + (res.templates_for_subject || 1) + '). The still was processed in memory and discarded.';
  } catch (e) { document.getElementById('faceResult').textContent = 'Enroll failed: ' + e.message; }
});
document.getElementById('btnMatch').addEventListener('click', async () => {
  try {
    const image_b64 = await faceStill();
    const res = await post('/face-match', {image_b64: image_b64});
    document.getElementById('faceResult').textContent = res.matched
      ? ('Match (observation, not a finding): ' + res.subject_id + ' — distance ' + res.distance + ', confidence ' + res.confidence + ' (' + res.backend + ').')
      : ('No match — closest distance ' + res.distance + ' against threshold ' + res.threshold + ' (' + res.backend + ').');
  } catch (e) { document.getElementById('faceResult').textContent = 'Match failed: ' + e.message; }
});
</script>
</body>
</html>
"""


def _csp_for(page: str) -> str:
    import base64 as _b64
    import hashlib as _hl
    import re as _re

    def digest(body: str) -> str:
        return "'sha256-" + _b64.b64encode(_hl.sha256(body.encode("utf-8")).digest()).decode("ascii") + "'"

    scripts = " ".join(digest(m) for m in _re.findall(r"<script[^>]*>(.*?)</script>", page, _re.S))
    styles = " ".join(digest(m) for m in _re.findall(r"<style[^>]*>(.*?)</style>", page, _re.S))
    return (
        f"default-src 'none'; script-src {scripts}; style-src {styles}; connect-src 'self'; "
        "media-src 'self' blob:; img-src 'self' blob: data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )


_CAPTURE_CSP = _csp_for(_CAPTURE_HTML)
_PERMISSIONS_POLICY = "microphone=(self), camera=(self)"
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class _IngestRateLimiter:
    """Per-IP rate limiter. Chunk/turn ingest gets its own generous
    budget (10/s at real-time pace must never trip the dashboard's
    120/min rule); other routes share a stricter budget."""

    def __init__(self, ingest_limit: int = 600, other_limit: int = 120, window_s: float = 60.0):
        self.ingest_limit = ingest_limit
        self.other_limit = other_limit
        self.window_s = window_s
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, ingest: bool = False) -> bool:
        now = time.time()
        limit = self.ingest_limit if ingest else self.other_limit
        with self._lock:
            q = [t for t in self._hits.get(key, []) if now - t < self.window_s]
            if len(q) >= limit:
                self._hits[key] = q
                return False
            q.append(now)
            self._hits[key] = q
            return True


class LiveAvServer:
    """Stdlib HTTP server for one :class:`LiveSession`.

    Serves the officer capture page and the ingest endpoints. Binds
    loopback by default so media stays on the capture host. Ingest
    requires the per-session token minted at session start.
    """

    def __init__(self, session: LiveSession, host: str = "127.0.0.1", port: int = 0):
        self.session = session
        self.host = host
        self.port = port
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._rate = _IngestRateLimiter()

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        if self._server is not None:
            return
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _authorized(self) -> bool:
                auth = self.headers.get("Authorization", "")
                if auth == f"Bearer {outer.session.ingest_token}":
                    return True
                if self.headers.get("X-Ingest-Token") == outer.session.ingest_token:
                    return True
                parsed = urlparse(self.path)
                import urllib.parse as _up

                q = _up.parse_qs(parsed.query)
                return (q.get("token") or [None])[0] == outer.session.ingest_token

            def _origin_ok(self) -> bool:
                origin = self.headers.get("Origin")
                if not origin:
                    return True
                try:
                    u = urlparse(origin)
                    return u.scheme in ("http", "https") and u.hostname in _LOCAL_HOSTS
                except ValueError:
                    return False

            def _rate_ok(self, *, ingest: bool = False) -> bool:
                key = self.client_address[0] if self.client_address else "unknown"
                return outer._rate.allow(key, ingest=ingest)

            def _respond(self, code: int, body: bytes = b"", content_type: Optional[str] = None, csp: Optional[str] = None, extra: Optional[Dict[str, str]] = None) -> None:
                try:
                    self.send_response(code)
                    if content_type:
                        self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Referrer-Policy", "no-referrer")
                    if csp:
                        self.send_header("Content-Security-Policy", csp)
                    self.send_header("Permissions-Policy", _PERMISSIONS_POLICY)
                    if extra:
                        for k, v in extra.items():
                            self.send_header(k, v)
                    self.end_headers()
                    if body:
                        self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def _json(self, code: int, payload: Any) -> None:
                self._respond(code, json.dumps(payload, default=str).encode("utf-8"), "application/json")

            def _read_json(self, max_bytes: int = 65536) -> Dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length > max_bytes:
                    raise ValueError("request body too large")
                raw = self.rfile.read(length) if length else b""
                if not raw:
                    return {}
                data = json.loads(raw.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("request body must be a JSON object")
                return data

            def _session_path(self) -> Optional[str]:
                parsed = urlparse(self.path)
                parts = [p for p in parsed.path.split("/") if p]
                # /live/v1/<session>/<action...> or /live/ (page)
                if len(parts) >= 3 and parts[0] == "live" and parts[1] == "v1":
                    return parts[2], parts[3:]
                return None

            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path in ("/", "/live", "/live/"):
                    if not self._authorized():
                        self._json(401, {"ok": False, "error": "unauthorized"})
                        return
                    if not self._rate_ok():
                        self._json(429, {"ok": False, "error": "rate_limited"})
                        return
                    self._respond(200, _CAPTURE_HTML.encode("utf-8"), "text/html; charset=utf-8", csp=_CAPTURE_CSP)
                    return
                sp = self._session_path()
                if sp is None:
                    self._respond(404)
                    return
                sid, rest = sp
                if sid != outer.session.session_id:
                    self._json(404, {"ok": False, "error": "unknown_session"})
                    return
                if not self._authorized():
                    self._json(401, {"ok": False, "error": "unauthorized"})
                    return
                if not self._rate_ok():
                    self._json(429, {"ok": False, "error": "rate_limited"})
                    return
                if rest == ["state"]:
                    payload = outer.session.status()
                    payload.update({
                        "cues_shown": list(outer.session.cues_shown),
                        "turns": list(outer.session.transcript),
                        "timeline": list(outer.session.timeline),
                        "video_windows": list(outer.session.video_windows),
                    })
                    self._json(200, payload)
                    return
                if rest == ["events"]:
                    self._sse()
                    return
                self._respond(404)

            def _sse(self) -> None:
                import urllib.parse as _up

                q = _up.parse_qs(urlparse(self.path).query)
                last_id = int((q.get("last_event_id") or ["0"])[0] or 0)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Permissions-Policy", _PERMISSIONS_POLICY)
                self.end_headers()
                try:
                    pending = outer.session.events_since(last_id)
                    for ev in pending:
                        self.wfile.write(f"id: {ev['id']}\nevent: {ev['kind']}\ndata: {json.dumps(ev['data'], default=str)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    # Hold the stream briefly so a live client sees pushes;
                    # clients reconnect with Last-Event-ID to resume.
                    deadline = time.time() + 25.0
                    seen = pending[-1]["id"] if pending else last_id
                    while time.time() < deadline:
                        time.sleep(0.2)
                        fresh = outer.session.events_since(seen)
                        for ev in fresh:
                            self.wfile.write(f"id: {ev['id']}\nevent: {ev['kind']}\ndata: {json.dumps(ev['data'], default=str)}\n\n".encode("utf-8"))
                            seen = ev["id"]
                        if fresh:
                            self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_POST(self):  # noqa: N802
                sp = self._session_path()
                if sp is None:
                    self._respond(404)
                    return
                sid, rest = sp
                if sid != outer.session.session_id:
                    self._json(404, {"ok": False, "error": "unknown_session"})
                    return
                if not self._authorized():
                    self._json(401, {"ok": False, "error": "unauthorized"})
                    return
                ingest_route = rest in (["turn"], ["typed-turn"], ["chunk"], ["video-window"])
                if not self._rate_ok(ingest=ingest_route):
                    self._json(429, {"ok": False, "error": "rate_limited"})
                    return
                if not self._origin_ok():
                    self._json(403, {"ok": False, "error": "origin_not_allowed"})
                    return
                try:
                    max_bytes = 10 * 1024 * 1024 if rest in (["face-enroll"], ["face-match"]) else 65536
                    data = self._read_json(max_bytes=max_bytes)
                except Exception as exc:
                    self._json(400, {"ok": False, "error": str(exc)})
                    return
                try:
                    if rest == ["start"]:
                        modality = str(data.get("modality") or "")
                        if modality == "audio_features":
                            result = outer.session.set_timing_enabled(True)
                        else:
                            result = outer.session.start(modality)
                        self._json(200, {"ok": True, **result})
                    elif rest == ["stop"]:
                        result = outer.session.stop(
                            str(data.get("reason") or "officer_stop"),
                            modalities=data.get("modalities"),
                        )
                        self._json(200, {"ok": True, **result})
                    elif rest == ["turn"]:
                        result = outer.session.ingest_final_turn(data, source="browser-stt")
                        self._json(200, {"ok": True, **result})
                    elif rest == ["typed-turn"]:
                        result = outer.session.ingest_final_turn(data, source="typed")
                        self._json(200, {"ok": True, **result})
                    elif rest == ["chunk"]:
                        result = outer.session.ingest_audio_chunk(int(data.get("seq", 0)), int(data.get("n_bytes", 0)))
                        self._json(200, {"ok": True, **result})
                    elif rest == ["video-window"]:
                        result = outer.session.ingest_video_window(data)
                        self._json(200, {"ok": True, **result})
                    elif rest == ["face-enroll"]:
                        image_b64 = str(data.get("image_b64") or "")
                        if not image_b64:
                            raise ValueError("image_b64 is required")
                        result = outer.session.enroll_face(str(data.get("subject_id") or ""), base64.b64decode(image_b64))
                        self._json(200, {"ok": True, **result})
                    elif rest == ["face-match"]:
                        image_b64 = str(data.get("image_b64") or "")
                        if not image_b64:
                            raise ValueError("image_b64 is required")
                        result = outer.session.match_face(base64.b64decode(image_b64))
                        self._json(200, {"ok": True, **result})
                    else:
                        self._respond(404)
                except GateError as exc:
                    self._json(403, {"ok": False, "error_code": exc.code, "error": exc.message})
                except (ValueError, FaceRecError) as exc:
                    code = getattr(exc, "code", "invalid_request")
                    self._json(400, {"ok": False, "error_code": code, "error": str(exc)})
                except Exception as exc:  # never leak a stack trace to the officer page
                    self._json(500, {"ok": False, "error": f"live input fault: {exc}"})

            def log_message(self, *args):  # noqa: D401
                return

        class Server(ThreadingHTTPServer):
            daemon_threads = True

            def get_request(self):  # noqa: N802 - TCP_NODELAY on every accepted socket
                sock, addr = super().get_request()
                try:
                    import socket as _socket

                    sock.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1)
                except Exception:
                    pass
                return sock, addr

        self._server = Server((self.host, self.port), Handler)
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/?token={self.session.ingest_token}&session={self.session.session_id}"

    def __enter__(self) -> "LiveAvServer":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
