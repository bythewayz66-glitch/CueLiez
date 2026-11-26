"""Real face recognition: enrollment + embedding-distance matching.

This module is REAL recognition, not a placeholder. It uses, when the
optional dependency is installed:

- Haar-cascade face detection (OpenCV, bundled cascade),
- 68-point facial landmarks (OpenCV FacemarkLBF) to align each face by the
  eye centres + nose tip before embedding,
- 128-dimensional face embeddings from the OpenFace ``nn4.small2.v1.t7``
  Torch model (CMU Satya Lab, open model; see model provenance below),
  L2-normalised, compared by Euclidean distance.

Matching: a probe embedding is compared with each enrolled subject's mean
embedding. ``matched`` is True only when the smallest distance is at or
below ``match_threshold`` (default 0.9). The reported ``score`` is a linear
similarity derived from that distance, ``score = clamp(1 - distance / 2)``
(2.0 is the maximum L2 distance between two unit vectors). It is a
similarity score, NOT a probability and NOT a certainty of identity; the
observation layer labels it as an embedding-distance match cue for human
review, never a definitive identification.

Model provenance (measured in this repo, 2026-11-25, venv with
``opencv-contrib-python-headless==4.10.0.84``):

- Embedding model: OpenFace ``nn4.small2.v1.t7`` (31 MB), downloaded from
  https://storage.cmusatyalab.org/openface-models/nn4.small2.v1.t7
  (CMU). Test fixture copy: ``tests/fixtures/face/models/nn4.small2.v1.t7``.
- Landmark model: FacemarkLBF ``lbfmodel.yaml`` (56 MB), downloaded from
  https://raw.githubusercontent.com/kurnianggoro/GSOC2017/master/data/lbfmodel.yaml
  (OpenCV contrib sample data). Test fixture copy:
  ``tests/fixtures/face/models/lbfmodel.yaml``.
- Haar cascade: bundled with OpenCV (``cv2.data.haarcascades``).
- Measured separation on the 5-photo fixture
  (``tests/fixtures/face/``: obama/obama2/obama3, biden/biden2 — real
  public-domain White House portraits): aligned embeddings give
  same-person distances 0.49-0.75 and different-person distances
  1.15-1.25 across all 10 pairs, so the default threshold 0.9 separates
  this fixture. That is a 5-photo measurement, NOT a validated operating
  point: any deployment MUST calibrate the threshold on its own enrolled
  population before relying on matches. Unaligned (Haar crop only)
  embeddings do NOT separate reliably (same-person up to 0.80,
  different-person down to 0.93, and one same-person pair at 1.10), which
  is why alignment is the default path and the unaligned path is flagged
  in its evidence as ``aligned: false``.

What this module does NOT do:

- It does not identify anyone who was never enrolled. A probe with no
  enrolled subject within threshold returns ``matched=False``.
- It creates no biometric template unless the caller enrolls. Templates
  are in-memory mean embeddings by default.
- It makes no network call and transmits nothing. Model files are loaded
  from local paths only.
- It is not a finding about a person. Matching is a cue for human review.

Biometric templates are sensitive data:

- Templates (mean 128-d embeddings per enrolled subject) live only in
  memory unless the caller explicitly persists them through
  :class:`FaceTemplateStore` with an explicit consent record
  (``consent_record`` describing attester, jurisdiction and purpose).
- :meth:`FaceTemplateStore.delete_subject` / ``delete_all`` remove
  templates; retention is the caller's responsibility and must be
  documented per deployment (default: session only, nothing written).
- Never store templates alongside a transcript or sealed package without
  explicit consent and a documented retention/deletion plan.

Optional dependency (NOT required by the CueLiez core, which stays
stdlib-only): ``opencv-contrib-python-headless==4.10.0.84`` — declared as
the ``face`` extra in ``pyproject.toml``. OpenCV 5.x removed the Torch
model importer (``cv2.dnn.readNetFromTorch``), so 4.10 is pinned for this
extra. Without it, :func:`face_available` is False and every public
entry point fails closed with :class:`FaceRecognitionUnavailable`
instead of producing a score.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

try:  # Optional dependency; core stays stdlib-only.
    import cv2 as _cv2
    import numpy as _np

    _CV2_OK = (
        hasattr(_cv2, "face")
        and hasattr(_cv2.face, "createFacemarkLBF")
        and hasattr(_cv2.dnn, "readNetFromTorch")
    )
except Exception:  # pragma: no cover - import failure path
    _cv2 = None  # type: ignore[assignment]
    _np = None  # type: ignore[assignment]
    _CV2_OK = False

# Default operating point. Measured on the 5-photo fixture (see module
# docstring); NOT a validated operating point for any other population.
DEFAULT_MATCH_THRESHOLD = 0.9
EMBEDDING_DIM = 128
# Canonical eye/nose positions in the 96x96 aligned face (OpenFace input).
_ALIGNED_EYE_LEFT = (30.0, 32.0)
_ALIGNED_EYE_RIGHT = (66.0, 32.0)
_ALIGNED_NOSE = (48.0, 55.0)


class FaceRecognitionUnavailable(RuntimeError):
    """The optional face-recognition dependency is not installed."""


class NoFaceDetected(ValueError):
    """No face could be detected in the supplied image."""


class FaceRecognitionError(RuntimeError):
    """Face detection/embedding failed for a supplied image."""


def face_available() -> bool:
    """True when the optional OpenCV face-recognition stack is importable."""
    return bool(_CV2_OK)


def _require_cv2() -> None:
    if not _CV2_OK or _cv2 is None:
        raise FaceRecognitionUnavailable(
            "Face recognition needs the optional 'face' extra: "
            "pip install 'cueliez[face]' (opencv-contrib-python-headless==4.10.0.84). "
            "Core CueLiez stays stdlib-only; no match score is produced without it."
        )


@dataclass
class FaceMatch:
    """Result of matching one probe image against enrolled templates."""

    matched: bool
    subject_id: Optional[str]
    distance: Optional[float]
    score: float
    threshold: float
    model: str = "openface/nn4.small2.v1.t7"
    aligned: bool = True
    enrolled_subjects: Tuple[str, ...] = ()
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "matched": self.matched,
            "subject_id": self.subject_id,
            "distance": self.distance,
            "score": round(self.score, 4),
            "threshold": self.threshold,
            "model": self.model,
            "aligned": self.aligned,
            "enrolled_subjects": list(self.enrolled_subjects),
        }
        if self.detail:
            out["detail"] = self.detail
        return out


def distance_to_score(distance: float) -> float:
    """Linear similarity from an L2 distance between unit embeddings.

    Max L2 distance between two unit vectors is 2.0, so
    ``1 - distance/2`` maps distance 0 -> 1.0 and distance 2 -> 0.0.
    Documented similarity, NOT a probability of identity.
    """
    return max(0.0, min(1.0, 1.0 - float(distance) / 2.0))


class FaceRecognizer:
    """Enrollment + embedding-distance matching with real image input.

    Parameters
    ----------
    model_path: local path to ``nn4.small2.v1.t7`` (OpenFace Torch model).
    landmark_model_path: local path to ``lbfmodel.yaml`` (optional; when
        absent, faces are embedded from the Haar crop without alignment and
        matches are flagged ``aligned: false``).
    match_threshold: max embedding distance counted as a match.
    """

    def __init__(
        self,
        model_path: str | os.PathLike,
        landmark_model_path: Optional[str | os.PathLike] = None,
        *,
        match_threshold: float = DEFAULT_MATCH_THRESHOLD,
    ) -> None:
        _require_cv2()
        self.model_path = str(model_path)
        self.landmark_model_path = str(landmark_model_path) if landmark_model_path else None
        self.match_threshold = float(match_threshold)
        if not os.path.exists(self.model_path):
            raise FaceRecognitionError(f"Face embedding model not found: {self.model_path}")
        self._net = _cv2.dnn.readNetFromTorch(self.model_path)
        self._cascade = _cv2.CascadeClassifier(
            _cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self._facemark = None
        if self.landmark_model_path:
            if not os.path.exists(self.landmark_model_path):
                raise FaceRecognitionError(
                    f"Landmark model not found: {self.landmark_model_path}"
                )
            self._facemark = _cv2.face.createFacemarkLBF()
            self._facemark.loadModel(self.landmark_model_path)
        # subject_id -> list of unit embeddings (one per enrollment image)
        self._embeddings: Dict[str, List[Any]] = {}

    # -- image handling -------------------------------------------------
    def _load_image(self, image: Any) -> Any:
        if isinstance(image, (str, os.PathLike)):
            img = _cv2.imread(str(image))
            if img is None:
                raise FaceRecognitionError(f"Could not read image file: {image}")
            return img
        arr = _np.asarray(image)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise FaceRecognitionError("Image array must be HxWx3 (BGR).")
        return arr

    def detect_faces(self, image: Any) -> List[Tuple[int, int, int, int]]:
        """Return ``(x, y, w, h)`` boxes for faces found in ``image``."""
        _require_cv2()
        img = self._load_image(image)
        gray = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(gray, 1.1, 4)
        return [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]

    def embed(self, image: Any) -> Tuple[Any, bool]:
        """Return ``(unit_embedding_128, aligned)`` for the largest face.

        Raises :class:`NoFaceDetected` when no face is found.
        """
        _require_cv2()
        img = self._load_image(image)
        gray = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(gray, 1.1, 4)
        if len(faces) == 0:
            raise NoFaceDetected("No face detected in the supplied image.")
        x, y, w, h = [int(v) for v in max(faces, key=lambda b: b[2] * b[3])]
        face_bgr = img[y : y + h, x : x + w]
        aligned = False
        if self._facemark is not None:
            try:
                ok, landmarks = self._facemark.fit(gray, _np.array([[x, y, w, h]]))
                if ok and len(landmarks):
                    pts = landmarks[0][0]
                    left_eye = pts[36:42].mean(axis=0)
                    right_eye = pts[42:48].mean(axis=0)
                    nose = pts[30]
                    src = _np.float32([left_eye, right_eye, nose])
                    dst = _np.float32([_ALIGNED_EYE_LEFT, _ALIGNED_EYE_RIGHT, _ALIGNED_NOSE])
                    mat = _cv2.getAffineTransform(src, dst)
                    face_bgr = _cv2.warpAffine(img, mat, (96, 96))
                    aligned = True
            except Exception:
                # Landmark failure falls back to the Haar crop (flagged).
                face_bgr = img[y : y + h, x : x + w]
                aligned = False
        blob = _cv2.dnn.blobFromImage(face_bgr, 1.0 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=False)
        self._net.setInput(blob)
        vec = self._net.forward().flatten().astype(_np.float64)
        norm = float(_np.linalg.norm(vec))
        if norm == 0.0:
            raise FaceRecognitionError("Embedding model returned a zero vector.")
        return vec / norm, aligned

    # -- enrollment / matching ------------------------------------------
    def enroll(self, subject_id: str, image: Any) -> Dict[str, Any]:
        """Enroll one image for ``subject_id``; returns enrollment evidence.

        The caller must have face-recognition consent + jurisdiction for
        this subject before calling (enforced by the observer layer).
        """
        if not str(subject_id).strip():
            raise ValueError("subject_id is required for enrollment.")
        vec, aligned = self.embed(image)
        self._embeddings.setdefault(str(subject_id), []).append(vec)
        return {
            "subject_id": str(subject_id),
            "enrollment_images": len(self._embeddings[str(subject_id)]),
            "aligned": aligned,
            "embedding_dim": EMBEDDING_DIM,
        }

    def enrolled_subjects(self) -> List[str]:
        return sorted(self._embeddings)

    def _mean_embedding(self, subject_id: str) -> Any:
        vecs = self._embeddings[subject_id]
        mean = _np.mean(vecs, axis=0)
        return mean / float(_np.linalg.norm(mean))

    def match(self, image: Any) -> FaceMatch:
        """Match a probe image against enrolled subjects (real distances)."""
        if not self._embeddings:
            return FaceMatch(
                matched=False,
                subject_id=None,
                distance=None,
                score=0.0,
                threshold=self.match_threshold,
                enrolled_subjects=(),
                detail="no_enrolled_subjects",
            )
        vec, aligned = self.embed(image)
        best_id: Optional[str] = None
        best_dist: Optional[float] = None
        for subject_id in self.enrolled_subjects():
            dist = float(_np.linalg.norm(vec - self._mean_embedding(subject_id)))
            if best_dist is None or dist < best_dist:
                best_dist, best_id = dist, subject_id
        assert best_dist is not None and best_id is not None
        matched = best_dist <= self.match_threshold
        return FaceMatch(
            matched=matched,
            subject_id=best_id if matched else None,
            distance=round(best_dist, 4),
            score=distance_to_score(best_dist),
            threshold=self.match_threshold,
            aligned=aligned,
            enrolled_subjects=tuple(self.enrolled_subjects()),
            detail="closest_enrolled_subject" if matched else "no_subject_within_threshold",
        )

    def clear(self) -> None:
        """Drop all in-memory enrollment templates."""
        self._embeddings.clear()


class FaceTemplateStore:
    """Consent-gated persistence for face templates (mean embeddings).

    Templates are sensitive biometric data. Nothing is written unless the
    caller passes an explicit ``consent_record`` (a mapping with at least
    ``attested_by`` and ``jurisdiction``) to :meth:`save`. The file holds
    only subject ids + 128-d mean embeddings (``.npz``); no images, no
    names beyond the caller-supplied subject ids. Delete with
    :meth:`delete_subject` / :meth:`delete_all`; retention (how long a
    saved file may exist) is a deployment decision that must be recorded
    alongside the consent record — this store sets no retention itself
    and never transmits anything.
    """

    def __init__(self, recognizer: FaceRecognizer) -> None:
        self.recognizer = recognizer

    def save(self, path: str | os.PathLike, *, consent_record: Mapping[str, Any]) -> Dict[str, Any]:
        attester = str((consent_record or {}).get("attested_by") or "").strip()
        jurisdiction = str((consent_record or {}).get("jurisdiction") or "").strip()
        if not attester or not jurisdiction:
            raise ValueError(
                "Face templates may be saved only with an explicit consent record "
                "(attested_by and jurisdiction are required)."
            )
        _require_cv2()
        subjects = self.recognizer.enrolled_subjects()
        payload = {f"subject::{s}": self.recognizer._mean_embedding(s) for s in subjects}
        _np.savez(str(path), **payload)
        return {
            "path": str(path),
            "subjects": subjects,
            "attested_by": attester,
            "jurisdiction": jurisdiction,
            "note": "Biometric templates saved with explicit consent; delete per retention plan.",
        }

    def load(self, path: str | os.PathLike) -> List[str]:
        _require_cv2()
        data = _np.load(str(path), allow_pickle=False)
        loaded: List[str] = []
        for key in data.files:
            if not key.startswith("subject::"):
                continue
            subject_id = key[len("subject::") :]
            self.recognizer._embeddings.setdefault(subject_id, []).append(data[key])
            loaded.append(subject_id)
        return sorted(loaded)

    def delete_subject(self, subject_id: str) -> bool:
        return self.recognizer._embeddings.pop(str(subject_id), None) is not None

    def delete_all(self) -> None:
        self.recognizer.clear()
