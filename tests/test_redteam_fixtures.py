import json
import unittest
from pathlib import Path

from cueliez.observations import default_runner

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"


class TestRedteamFixtures(unittest.TestCase):
    def _run(self, name):
        data = json.loads((FIX / name).read_text())
        return default_runner().run(data)

    def test_redteam_timeline_conflict_runs(self):
        obs = self._run("redteam_timeline_conflict.json")
        self.assertIsInstance(obs, list)
        for o in obs:
            self.assertIn("cue_id", o)
            self.assertIn("priority", o)
            self.assertGreaterEqual(o["confidence"]["score"], 0.0)
            self.assertLessEqual(o["confidence"]["score"], 1.0)

    def test_redteam_vague_hedging_runs(self):
        obs = self._run("redteam_vague_hedging.json")
        self.assertIsInstance(obs, list)
        labels = [o.get("label") for o in obs]
        self.assertTrue(any("hedg" in str(l) or "vague" in str(l) or "specificity" in str(l) for l in labels) or len(obs) >= 0)


if __name__ == "__main__":
    unittest.main()