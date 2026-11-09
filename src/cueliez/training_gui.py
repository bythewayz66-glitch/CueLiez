"""Web-based training GUI for CueLiez (not CLI training).

Provides a local browser UI for: module browsing/viewing (with optional local
media: images/screenshots/video), interactive scored quizzes, self-training
sandbox/playground (observation cues on sample or pasted transcripts), and
minimal credential record workflows. Observation/cue-only; no verdicts.
"""

from __future__ import annotations

import html
import json
import mimetypes
import threading
import time
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

from .audit import audit_event
from .compliance.records import TrainingRecordStore
from .compliance.training import (
    TrainingAcknowledgement,
    domain_training,
    get_training_bundle,
    validate_training_ack,
)
from .delivery.events import cues_from_observations
from .observations import default_runner

DEFAULT_MEDIA_DIR = Path(__file__).resolve().parents[2] / "docs" / "training" / "media"


def _quizzes() -> Dict[str, List[Dict[str, Any]]]:
    # Real, domain-aligned interactive quiz content (observation/cue-only).
    common = [
        {"id": "c1", "q": "What does CueLiez produce for human review?", "choices": ["Deception verdicts", "Observation cues/indicators", "Guilt findings", "Clinical diagnoses"], "answer": 1,
         "explain": "CueLiez produces observation cues/indicators for human review, not verdicts or diagnoses."},
        {"id": "c2", "q": "Who makes final judgments and decisions?", "choices": ["The system automatically", "Only the model", "The human operator/professional", "The dashboard"], "answer": 2,
         "explain": "Human judgment remains required; the system supports inquiry with cues."},
        {"id": "c3", "q": "Which claim is prohibited?", "choices": ["A cue suggests a possible inconsistency", "The system outputs a prohibited definitive finding about truthfulness", "An indicator is probabilistic", "A follow-up question may clarify"], "answer": 1,
         "explain": "Definitive truthfulness/guilt findings are prohibited; CueLiez provides observation cues only."},
    ]
    gov = common + [
        {"id": "g1", "q": "In government mode, what may be required before sealing high-priority cues?", "choices": ["Nothing", "Dual-control", "Automatic clearance", "Diagnosis"], "answer": 1,
         "explain": "Government/high-stakes workflows may require dual-control and gate discipline."},
    ]
    leg = common + [
        {"id": "l1", "q": "How should a cue be used in a legal interview?", "choices": ["As proof of guilt", "To guide a neutral clarifying question", "As a detention decision", "As a numerical credibility verdict"], "answer": 1,
         "explain": "Cues guide human-led clarification; they are not legal findings."},
    ]
    med = common + [
        {"id": "m1", "q": "In clinical/support contexts, CueLiez cues are:", "choices": ["Diagnoses", "Non-diagnostic communication/history-taking support", "Treatment decisions", "Credibility determinations"], "answer": 1,
         "explain": "Clinical-context use is non-diagnostic and human-led."},
    ]
    thrp = common + [
        {"id": "t1", "q": "In therapy/support contexts, a cue should prompt:", "choices": ["Adversarial accusation", "Supportive clarification and pacing", "Automated care decisions", "Risk adjudication"], "answer": 1,
         "explain": "Use cues for supportive, human-led clarification and pacing."},
    ]
    return {"gov": gov, "leg": leg, "med": med, "thrp": thrp}
