"""Kilo hardening pass: observer precision/coverage on owner demo transcripts.

Validates post-hardening cue behavior for docs/examples/owner_{clean,conflict,hedging}_interview.json.
Observer/cue-contract checks only (seal/gate integrity covered by iceman hardening tests).
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from cueliez.observations import default_runner
from cueliez.observations.base import FORBIDDEN_LABELS

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "docs" / "examples"

FORBIDDEN_CUE_TEXT = re.compile(
    r"\b(lie\s+detector|detects?\s+lies?|lie\s+detection|truth\s+detector|truth\s+score|"
    r"proves?\s+deception|confirms?\s+(?:lying|deception)|subject\s+is\s+lying|"
    r"\bguilty\b|\bdiagnosis\b|deception_confirmed|polygraph)\b",
    re.I,
)


def _load(name: str):
    with open(EXAMPLES / name, encoding="utf-8") as f:
        return json.load(f)


def _observations(name: str):
    pkg = default_runner().build_package(_load(name), session_id=f"kilo-hardening-{name}")
    return pkg.get("observations") or []


class HardeningOwnerTranscriptsKilo(unittest.TestCase):
    def _assert_common_contract(self, obs):
        for o in obs:
            label = str(o.get("label") or "")
            self.assertTrue(label.strip())
            self.assertNotIn(label.lower(), FORBIDDEN_LABELS)
            conf = o.get("confidence") or {}
            self.assertTrue(str(conf.get("model_id") or "").strip())
            score = conf.get("score")
            self.assertIsInstance(score, (int, float))
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
            self.assertTrue(str(o.get("cue_id") or "").strip(), f"missing cue_id: {o}")
            self.assertIn(o.get("priority"), ("normal", "high"), f"invalid priority: {o}")
            cue = str(o.get("cue") or "")
            m = FORBIDDEN_CUE_TEXT.search(f"{label} {cue}")
            self.assertIsNone(m, f"forbidden verdict language in cue: {m.group(0) if m else ''} :: {o}")

    def test_clean_zero_cues_after_time_approx_hardening(self):
        obs = _observations("owner_clean_interview.json")
        self._assert_common_contract(obs)
        self.assertEqual(len(obs), 0, f"expected 0 cues on clean transcript, got {[o.get('label') for o in obs]}")

    def test_conflict_has_timeline_cue_with_source_quotes(self):
        obs = _observations("owner_conflict_interview.json")
        self._assert_common_contract(obs)
        timeline = [
            o for o in obs
            if o.get("label") == "multiple_time_references_present"
            or o.get("method") == "cueliez.observations.consistency.timeline_inconsistency/v1"
        ]
        self.assertTrue(timeline, f"expected timeline/consistency cue, got {[o.get('method') for o in obs]}")
        ev = timeline[0].get("evidence") or {}
        self.assertTrue(ev.get("source_texts"), f"timeline cue missing source_texts: {ev}")
        refs = [str(r).lower() for r in (ev.get("distinct_time_refs") or [])]
        joined = " ".join(refs)
        for token in ("eight", "nine", "ten"):
            self.assertIn(token, joined, f"expected time ref {token!r} in {refs}")

    def test_hedging_transcript_cues_contract_and_deterministic(self):
        obs = _observations("owner_hedging_interview.json")
        self._assert_common_contract(obs)
        labels = [o.get("label") for o in obs]
        self.assertTrue(
            any("hedg" in str(l) for l in labels),
            f"expected hedging cues, got {labels}",
        )
        # Deterministic cue_ids across identical runs.
        obs2 = _observations("owner_hedging_interview.json")
        self.assertEqual([o.get("cue_id") for o in obs], [o.get("cue_id") for o in obs2])


if __name__ == "__main__":
    unittest.main()
