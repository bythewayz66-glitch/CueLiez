import unittest

from cueliez.gates import seal_observation_package, SessionGateState, record_consent
from cueliez.observations import ObservationRunner, default_runner, full_runner
from cueliez.observations.base import FORBIDDEN_LABELS


class TestRunner(unittest.TestCase):
    def test_default_runner_produces_gate_compatible(self):
        t = [
            {"role": "subject", "text": "I think maybe I was around there doing stuff.", "response_latency_ms": 4000},
            {"role": "subject", "text": "I did not do it, I swear honestly never."},
            {"role": "subject", "text": "Why would you ask that?"},
        ]
        pkg = default_runner().build_package(t, session_id="s1", annotations={"case": "x"})
        self.assertEqual(pkg["session_id"], "s1")
        self.assertEqual(pkg["annotations"]["case"], "x")
        sealed = seal_observation_package(pkg)
        self.assertEqual(sealed["epistemic_status"], "observed_indicator")
        self.assertFalse(sealed["is_definitive_finding"])

    def test_full_runner_handles_multimodal(self):
        t = [
            {"role": "subject", "text": "answer here", "heart_rate_bpm": 70, "gaze_aversion_ratio": 0.1},
            {"role": "subject", "text": "answer here", "heart_rate_bpm": 72, "gaze_aversion_ratio": 0.1},
            {"role": "subject", "text": "answer here", "heart_rate_bpm": 71, "gaze_aversion_ratio": 0.1},
            {"role": "subject", "text": "maybe not sure", "heart_rate_bpm": 140, "gaze_aversion_ratio": 0.9, "response_latency_ms": 5000},
        ]
        pkg = full_runner().build_package(t)
        sealed = seal_observation_package(pkg)
        # convergence may appear
        cats = {o.get("category") for o in sealed["observations"]}
        self.assertTrue(cats)

    def test_custom_runner(self):
        from cueliez.observations.linguistic import HedgingObserver
        r = ObservationRunner([HedgingObserver()])
        pkg = r.build_package([{"role": "subject", "text": "maybe I think perhaps"}])
        self.assertTrue(all(o["method"] == "cueliez.observations.linguistic.hedging/v1" for o in pkg["observations"]))

    def test_build_package_no_convergence(self):
        t = [{"role": "subject", "text": "hello"}]
        pkg = default_runner().build_package(t, include_convergence=False)
        self.assertFalse(any(o.get("category") == "multimodal" for o in pkg["observations"]))
        seal_observation_package(pkg)

    def test_seal_with_consent_state(self):
        t = [{"role": "subject", "text": "maybe perhaps I think"}]
        pkg = default_runner().build_package(t)
        s = SessionGateState(mode="interrogation")
        with self.assertRaises(Exception):
            seal_observation_package(pkg, s)
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        sealed = seal_observation_package(pkg, s)
        self.assertTrue(sealed["firewall"]["consent_rechecked"])

    def test_empty_transcript_emits_no_observations(self):
        for r in (default_runner(), full_runner()):
            pkg = r.build_package([])
            self.assertEqual(pkg["observations"], [])
            seal_observation_package(pkg)

    def test_observations_have_required_contract_fields(self):
        t = [
            {"role": "subject", "text": "I think maybe I was around there doing stuff.", "response_latency_ms": 4000},
            {"role": "subject", "text": "I did not enter the store. I entered the store.", "response_latency_ms": 500},
            {"role": "subject", "text": "I arrived at 9:00 pm and left at 10:30 pm."},
        ]
        for r in (default_runner(), full_runner()):
            pkg = r.build_package(t)
            for o in pkg["observations"]:
                self.assertIsInstance(o.get("label"), str)
                self.assertTrue(o["label"].strip())
                self.assertNotIn(str(o["label"]).lower(), FORBIDDEN_LABELS)
                conf = o.get("confidence") or {}
                self.assertIsInstance(conf.get("score"), (int, float))
                self.assertGreaterEqual(conf["score"], 0.0)
                self.assertLessEqual(conf["score"], 1.0)
                self.assertTrue(str(conf.get("model_id") or "").strip())
                self.assertTrue(str(o.get("method") or "").strip())
                self.assertTrue(str(o.get("category") or "").strip())
                self.assertIsInstance(o.get("evidence"), dict)
            seal_observation_package(pkg)

    def test_cue_text_has_no_forbidden_phrases(self):
        forbidden = (
            "lie detector", "detects lies", "lie detection", "truth detector", "truth machine",
            "polygraph", "proves deception", "confirms lying", "subject is lying",
            "guilty finding", "not guilty finding",
        )
        t = [
            {"role": "subject", "text": "I think maybe perhaps I was around there doing stuff.", "response_latency_ms": 5000},
            {"role": "subject", "text": "I did not do it, I swear honestly never. Why would you ask that?"},
            {"role": "subject", "text": "I entered the store. I did not enter the store."},
            {"role": "subject", "text": "I arrived at 9:00 pm and at 10:30 pm I was gone."},
        ]
        pkg = default_runner().build_package(t)
        for o in pkg["observations"]:
            cue = str(o.get("cue") or "").lower()
            for bad in forbidden:
                self.assertNotIn(bad, cue, f"forbidden phrase {bad!r} in cue: {o.get('cue')}")


if __name__ == "__main__":
    unittest.main()
