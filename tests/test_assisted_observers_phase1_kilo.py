"""Phase 1 (kilo): assisted observer prototype is feature-flagged off and not in runners."""
import unittest

from cueliez.observations import default_runner, full_runner
from cueliez.observations.assisted import ASSISTED_OBSERVERS_ENABLED, AssistedModelProvenance, AssistedObserverPrototype


class TestAssistedObserversPhase1Kilo(unittest.TestCase):
    def test_assisted_disabled_and_not_in_runners(self):
        self.assertFalse(ASSISTED_OBSERVERS_ENABLED)
        self.assertFalse(AssistedObserverPrototype().is_enabled())
        res = AssistedObserverPrototype().observe([{"role": "subject", "text": "maybe I think perhaps"}])
        self.assertEqual(res.to_dicts(), [])
        self.assertIn("assisted_observers_disabled", res.notes)
        for r in (default_runner(), full_runner()):
            ids = {getattr(o, "method_id", "") for o in r.observers}
            self.assertFalse(any("assisted" in i for i in ids), ids)

    def test_provenance_model_id_versioning(self):
        p = AssistedModelProvenance(provider="local", model="example", version="v1", adapter_version="a1", prompt_hash="abc")
        self.assertIn("local/example@v1", p.model_id)
        self.assertIn("a1", p.model_id)


if __name__ == "__main__":
    unittest.main()
