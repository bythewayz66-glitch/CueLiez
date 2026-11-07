import unittest

from cueliez.gates import seal_observation_package, SessionGateState, record_consent
from cueliez.observations import ObservationRunner, default_runner, full_runner


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


if __name__ == "__main__":
    unittest.main()
