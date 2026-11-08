import unittest

from cueliez.observations.base import Observation, ObservationResult, clamp01, make_observation


class TestBase(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(clamp01(-1), 0.0)
        self.assertEqual(clamp01(2), 1.0)
        self.assertEqual(clamp01(0.5), 0.5)

    def test_make_observation_valid(self):
        o = make_observation(label="signal_present", score=0.7, method_id="m/v1", category="linguistic",
                             evidence={"x": 1}, cue="ask", turn_index=2)
        d = o.to_dict()
        self.assertEqual(d["label"], "signal_present")
        self.assertEqual(d["confidence"]["score"], 0.7)
        self.assertEqual(d["confidence"]["model_id"], "m/v1")
        self.assertEqual(d["confidence"]["version"], "v1")
        self.assertEqual(d["method"], "m/v1")
        self.assertEqual(d["category"], "linguistic")
        self.assertEqual(d["evidence"], {"x": 1})
        self.assertEqual(d["turn_index"], 2)
        self.assertEqual(d["cue"], "ask")

    def test_rejects_forbidden_label(self):
        with self.assertRaises(ValueError):
            make_observation(label="lying", score=0.5, method_id="m/v1", category="x")
        with self.assertRaises(ValueError):
            make_observation(label="Guilty", score=0.5, method_id="m/v1", category="x")
        with self.assertRaises(ValueError):
            make_observation(label="deceptive", score=0.5, method_id="m/v1", category="x")
        with self.assertRaises(ValueError):
            make_observation(label="honest", score=0.5, method_id="m/v1", category="x")

    def test_rejects_bad_confidence(self):
        with self.assertRaises(ValueError):
            Observation(label="x", confidence={"score": 1.2, "model_id": "m"}, category="c", method="m")
        with self.assertRaises(ValueError):
            Observation(label="x", confidence={"score": 0.5, "model_id": ""}, category="c", method="m")

    def test_rejects_empty_method_or_category(self):
        with self.assertRaises(ValueError):
            Observation(label="x", confidence={"score": 0.5, "model_id": "m"}, category="", method="m")
        with self.assertRaises(ValueError):
            Observation(label="x", confidence={"score": 0.5, "model_id": "m"}, category="c", method="")
        with self.assertRaises(ValueError):
            make_observation(label="x", score=0.5, method_id="", category="c")

    def test_result_to_dicts(self):
        r = ObservationResult(method="m", observations=[
            make_observation(label="a", score=0.1, method_id="m/v1", category="c"),
        ])
        self.assertEqual(len(r.to_dicts()), 1)


if __name__ == "__main__":
    unittest.main()
