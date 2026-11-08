import json
import unittest
from pathlib import Path

from cueliez.observations import default_runner
from cueliez.observations.base import FORBIDDEN_LABELS
from cueliez.packs import get_pack

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "transcripts"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class TestGoldenFixtures(unittest.TestCase):
    def _assert_observation_contract(self, obs):
        for o in obs:
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
            ev = o.get("evidence")
            self.assertIsInstance(ev, dict)
            self.assertTrue(str(o.get("cue_id") or "").strip(), f"missing cue_id: {o}")
            self.assertIn(o.get("priority"), ("normal", "high"), f"invalid priority: {o}")
            # 0720: turn-anchored observations must include source text evidence.
            if o.get("turn_index") is not None:
                self.assertTrue(
                    ev.get("source_text") or ev.get("source_texts"),
                    f"turn-anchored observation missing source_text/source_texts: {o.get('label')} {o.get('method')}",
                )

    def test_clean_consistent_few_high_priority(self):
        t = load("clean_consistent.json")
        pkg = default_runner().build_package(t, session_id="fixture-clean")
        obs = pkg["observations"]
        self._assert_observation_contract(obs)
        high = [o for o in obs if o.get("priority") == "high"]
        self.assertLessEqual(len(high), 1, f"unexpected high-priority cues on clean fixture: {high}")
        # Also verify via leg pack
        pkg2 = get_pack("leg").build_package(t, session_id="fixture-clean-leg")
        self._assert_observation_contract(pkg2["observations"])

    def test_claim_conflict_fixture_triggers_expected(self):
        t = load("claim_conflict.json")
        pkg = default_runner().build_package(t, session_id="fixture-conflict")
        obs = pkg["observations"]
        self._assert_observation_contract(obs)
        methods = {o.get("method", "") for o in obs}
        labels = {o.get("label", "") for o in obs}
        self.assertTrue(
            "cueliez.observations.consistency.claim_conflict/v1" in methods
            or "possible_statement_conflict" in labels,
            f"expected claim conflict observation, got methods={sorted(methods)} labels={sorted(labels)}",
        )
        conflicts = [o for o in obs if o.get("label") == "possible_statement_conflict"]
        if conflicts:
            self.assertTrue(all(o.get("priority") == "high" for o in conflicts))
            self.assertTrue(all(str(o.get("cue_id", "")).startswith("cue-") for o in conflicts))

    def test_hedging_vague_fixture_triggers_linguistic(self):
        t = load("hedging_vague.json")
        pkg = default_runner().build_package(t, session_id="fixture-hedge-vague")
        obs = pkg["observations"]
        self._assert_observation_contract(obs)
        methods = {o.get("method", "") for o in obs}
        self.assertTrue(
            any("hedging" in m or "vagueness" in m or "detail_vagueness" in m for m in methods),
            f"expected hedging/vagueness observation, got {sorted(methods)}",
        )
        leg_obs = get_pack("leg").build_package(t)["observations"]
        self._assert_observation_contract(leg_obs)

    def test_evasion_short_fixture_triggers_behavioral(self):
        t = load("evasion_short.json")
        pkg = default_runner().build_package(t, session_id="fixture-evasion")
        obs = pkg["observations"]
        self._assert_observation_contract(obs)
        methods = {o.get("method", "") for o in obs}
        labels = {o.get("label", "") for o in obs}
        self.assertTrue(
            any("evasion" in m or "answer_length" in m for m in methods)
            or "question_deflection_markers_present" in labels
            or "notably_brief_response_observed" in labels,
            f"expected evasion/brief-response observation, got methods={sorted(methods)} labels={sorted(labels)}",
        )
        leg_obs = get_pack("leg").build_package(t)["observations"]
        self._assert_observation_contract(leg_obs)

    def test_multi_turn_drift_fixture_triggers_consistency(self):
        t = load("multi_turn_drift.json")
        pkg = default_runner().build_package(t, session_id="fixture-drift")
        obs = pkg["observations"]
        self._assert_observation_contract(obs)
        methods = {o.get("method", "") for o in obs}
        labels = {o.get("label", "") for o in obs}
        self.assertTrue(
            any("detail_drift" in m for m in methods) or "numeric_detail_drift_observed" in labels,
            f"expected detail drift observation, got methods={sorted(methods)} labels={sorted(labels)}",
        )
        leg_obs = get_pack("leg").build_package(t)["observations"]
        self._assert_observation_contract(leg_obs)

    def test_cue_ids_are_deterministic(self):
        t = load("claim_conflict.json")
        a = default_runner().build_package(t)["observations"]
        b = default_runner().build_package(t)["observations"]
        ids_a = sorted(o.get("cue_id") for o in a)
        ids_b = sorted(o.get("cue_id") for o in b)
        self.assertEqual(ids_a, ids_b)
        self.assertTrue(all(ids_a))


if __name__ == "__main__":
    unittest.main()
