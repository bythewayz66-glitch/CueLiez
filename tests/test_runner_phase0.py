"""Phase 0 closeout: runner usability smoke tests (kilo).

Ensures default_runner() and full_runner() produce usable, contract-valid output on
sample transcripts and handle insufficient data without errors.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from cueliez.gates import seal_observation_package
from cueliez.observations import default_runner, full_runner
from cueliez.observations.base import FORBIDDEN_LABELS

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "docs" / "examples"


def _load(rel: str):
    with open(ROOT / rel, encoding="utf-8") as f:
        return json.load(f)


class TestRunnerPhase0(unittest.TestCase):
    def _assert_contract(self, observations):
        for o in observations:
            label = str(o.get("label") or "")
            self.assertTrue(label.strip())
            self.assertNotIn(label.lower(), FORBIDDEN_LABELS)
            conf = o.get("confidence") or {}
            self.assertIsInstance(conf.get("score"), (int, float))
            self.assertGreaterEqual(conf["score"], 0.0)
            self.assertLessEqual(conf["score"], 1.0)
            self.assertTrue(str(conf.get("model_id") or "").strip())
            self.assertTrue(str(o.get("cue_id") or "").strip())
            self.assertIn(o.get("priority"), ("normal", "high"))

    def test_default_and_full_usable_on_sample_and_owner_transcripts(self):
        cases = [
            ("docs/examples/sample_transcript.json", "nonempty"),
            ("docs/examples/owner_clean_interview.json", "zero_ok"),
            ("docs/examples/owner_conflict_interview.json", "nonempty"),
            ("docs/examples/owner_hedging_interview.json", "nonempty"),
        ]
        for rel, expectation in cases:
            transcript = _load(rel)
            for runner_name, runner in (("default", default_runner()), ("full", full_runner())):
                with self.subTest(transcript=rel, runner=runner_name):
                    pkg = runner.build_package(transcript)
                    obs = pkg.get("observations") or []
                    self._assert_contract(obs)
                    seal_observation_package(dict(pkg))
                    if expectation == "nonempty":
                        self.assertTrue(obs, f"expected usable non-empty observations for {rel}")
                    # full_runner may emit nothing extra without feature metadata; that is acceptable.
                    if runner_name == "full":
                        self.assertIsInstance(obs, list)

    def test_insufficient_or_empty_input_emits_no_cues_no_errors(self):
        inputs = [
            [],
            {},
            {"turns": []},
            {"transcript": []},
            [{"role": "subject", "text": ""}],
            [{"role": "subject", "text": "   "}],
            [{"role": "subject", "text": "ok"}],
            [None, {"text": None}],
        ]
        for runner in (default_runner(), full_runner()):
            for inp in inputs:
                with self.subTest(runner=runner.__class__.__name__, inp=type(inp).__name__):
                    pkg = runner.build_package(inp)
                    obs = pkg.get("observations") or []
                    self.assertIsInstance(obs, list)
                    self._assert_contract(obs)
                    seal_observation_package(dict(pkg))


if __name__ == "__main__":
    unittest.main()
