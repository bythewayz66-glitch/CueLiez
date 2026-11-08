import os
import unittest

from cueliez.observations.assisted import (
    ASSISTED_OBSERVERS_ENABLED,
    clear_assisted_registry,
    make_multi_signal_assisted_adapter,
    merge_assisted_observations,
    register_assisted_observer,
    run_assisted_observers,
)


class TestAssistedMultiSignal(unittest.TestCase):
    def setUp(self):
        clear_assisted_registry()
        os.environ["CUELIEZ_ASSISTED_OBSERVERS"] = "1"

    def tearDown(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def test_disabled_by_default(self):
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)
        adapter = make_multi_signal_assisted_adapter()
        register_assisted_observer("multi", adapter)
        res = run_assisted_observers([{"role": "subject", "text": "I think maybe stuff happened, that guy did it."}], enabled=False)
        self.assertEqual(res, [])

    def test_enabled_runs(self):
        adapter = make_multi_signal_assisted_adapter()
        register_assisted_observer("multi", adapter)
        t = [{"role": "subject", "text": "I think maybe stuff happened, that guy did it."}]
        res = run_assisted_observers(t, enabled=True)
        self.assertTrue(res)
        obs = res[0].to_dicts()
        self.assertTrue(any(o["label"] == "multi_signal_language_pattern" for o in obs))

    def test_merge_additive(self):
        adapter = make_multi_signal_assisted_adapter()
        register_assisted_observer("multi", adapter)
        t = [{"role": "subject", "text": "I think maybe stuff happened, that guy did it."}]
        base = [{"label": "existing"}]
        out = merge_assisted_observations(base, t, enabled=True)
        self.assertGreater(len(out), 1)


if __name__ == "__main__":
    unittest.main()