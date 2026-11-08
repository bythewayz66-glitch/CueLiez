"""Phase 5 (kilo): red-team synthetic fixtures + gated-modality behavior tests.

Synthetic/de-identified regression checks only. No accuracy, credibility, deception, or finding claims.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from cueliez.observations import default_runner, full_runner
from cueliez.observations.base import FORBIDDEN_LABELS

ROOT = Path(__file__).resolve().parents[1]
REDTEAM = ROOT / "tests" / "fixtures" / "redteam"


def _load(name: str):
    return json.loads((REDTEAM / name).read_text(encoding="utf-8"))


class TestRedteamFixturesPhase5Kilo(unittest.TestCase):
    def _assert_valid(self, obs):
        for o in obs:
            self.assertNotIn(str(o.get("label", "")).lower(), FORBIDDEN_LABELS)
            conf = o.get("confidence") or {}
            self.assertTrue(str(conf.get("model_id") or "").strip())
            self.assertGreaterEqual(conf.get("score"), 0.0)
            self.assertLessEqual(conf.get("score"), 1.0)
            self.assertTrue(str(o.get("cue_id") or "").strip())

    def test_redteam_fixtures_contract_and_regression_counts(self):
        # Cue counts are regression/behavior checks on synthetic data only (no accuracy claims).
        cases = {
            "redteam_clean_routine.json": {"count": 0},
            "redteam_timeline_sequence_benign.json": {"count": 0},
            "redteam_evasion_short.json": {"count": 0},
            "redteam_mixed_hedging_memory.json": {"count": 3, "has": {"hedging_language_present"}},
            "redteam_numeric_detail_shift.json": {"count": 1},
        }
        runner = default_runner()
        for name, expect in cases.items():
            with self.subTest(fixture=name):
                obs = runner.build_package(_load(name)).get("observations") or []
                self._assert_valid(obs)
                self.assertEqual(len(obs), expect["count"], f"{name}: {[o.get('label') for o in obs]}")
                labels = {o.get("label") for o in obs}
                for req in expect.get("has", set()):
                    self.assertIn(req, labels, f"{name} missing {req}")

    def test_gated_modalities_off_by_default(self):
        # Feature/physio/visual observers are gated; not in default_runner, no extra cues without metadata.
        gated_prefixes = (
            "cueliez.observations.prosody.",
            "cueliez.observations.visual.",
            "cueliez.observations.physiological.",
        )
        default_methods = {getattr(o, "method_id", "") for o in default_runner().observers}
        self.assertFalse(any(m.startswith(gated_prefixes) for m in default_methods), default_methods)
        full = full_runner()
        full_methods = {getattr(o, "method_id", "") for o in full.observers}
        self.assertTrue(any(m.startswith(gated_prefixes) for m in full_methods))
        # Without feature metadata, full_runner must not emit gated-modality observations on text-only transcript.
        t = _load("redteam_clean_routine.json")
        obs = full.build_package(t).get("observations") or []
        self._assert_valid(obs)
        self.assertFalse(any(str(o.get("method", "")).startswith(gated_prefixes) for o in obs), obs)


if __name__ == "__main__":
    unittest.main()
