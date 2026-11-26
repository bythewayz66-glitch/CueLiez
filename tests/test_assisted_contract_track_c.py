"""Track C contract tests: ML/assisted observers (Phase 1).

Covers: (a) disabled assisted observers never emit anything and never
emit verdict-shaped data; (b) the enabled deterministic multi-signal
baseline emits real convergence observations on a hedging+vague
transcript and nothing on a clean transcript; (c) an assisted observer
that returns verdict-shaped data is rejected/filtered; (d) provenance
(model_id, version, adapter) is present on every assisted observation.
Also covers the runner opt-in wiring and the sealed-package epistemic
fields for assisted output. No network/ML calls anywhere in these tests.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cueliez.gates import seal_observation_package
from cueliez.observations import default_runner, full_runner
from cueliez.observations.assisted import (
    MULTI_SIGNAL_METHOD_ID,
    AssistedModelProvenance,
    MultiSignalAssistedObserver,
    clear_assisted_registry,
    is_verdict_shaped_observation,
    make_multi_signal_assisted_adapter,
    merge_assisted_observations,
    register_assisted_observer,
    run_assisted_observers,
    run_default_assisted_observers,
)
from cueliez.observations.base import ObservationResult, make_observation

# Transcript where hedging + vagueness + distancing converge on one turn.
CONVERGING = [
    {"role": "subject", "text": "I think maybe stuff happened, that guy did it, sort of."},
    {"role": "officer", "text": "Where were you at nine?"},
]
# Clean transcript: specific, no hedge/vague/distancing markers.
CLEAN = [
    {"role": "subject", "text": "I went to the store at 9:00 pm and bought milk and bread, then I drove home."},
    {"role": "subject", "text": "I arrived at the office at 8:00 am and stayed until 5:00 pm."},
]
# Tokens that must never appear anywhere in assisted output (checked as
# whole words / keys in the serialised output, not as substrings of
# unrelated words).
FORBIDDEN_TOKENS = ("lying", "deception_confirmed", "guilty", "truth_score")


def _assisted(obs):
    return [o for o in obs if "assisted" in str(o.get("method") or "")]


def _assert_no_forbidden(testcase, obs):
    blob = json.dumps(obs, ensure_ascii=False).lower()
    for tok in FORBIDDEN_TOKENS:
        testcase.assertNotIn(tok, blob, f"forbidden token {tok!r} in assisted output: {blob[:400]}")


class TestAssistedDisabled(unittest.TestCase):
    def setUp(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def tearDown(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def test_disabled_by_default_never_emits(self):
        register_assisted_observer("multi_signal", make_multi_signal_assisted_adapter())
        # Runner default: no assisted observations at all.
        for runner in (default_runner(), full_runner()):
            pkg = runner.build_package(CONVERGING)
            self.assertEqual(_assisted(pkg["observations"]), [])
            _assert_no_forbidden(self, pkg["observations"])
        # Explicit disabled run/merge: nothing, even with an adapter registered.
        self.assertEqual(run_assisted_observers(CONVERGING, enabled=False), [])
        self.assertEqual(run_default_assisted_observers(CONVERGING, enabled=False), [])
        base = [{"label": "existing"}]
        self.assertEqual(merge_assisted_observations(base, CONVERGING, enabled=False), base)

    def test_disabled_env_flag_off(self):
        self.assertEqual(os.environ.get("CUELIEZ_ASSISTED_OBSERVERS"), None)
        self.assertEqual(run_assisted_observers(CONVERGING), [])
        self.assertEqual(run_default_assisted_observers(CONVERGING), [])


class TestAssistedMultiSignalEnabled(unittest.TestCase):
    def setUp(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def tearDown(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def test_enabled_emits_convergence_observation(self):
        pkg = default_runner(enable_assisted=True).build_package(CONVERGING)
        assisted = _assisted(pkg["observations"])
        self.assertEqual(len(assisted), 1)
        obs = assisted[0]
        self.assertEqual(obs["label"], "multi_signal_language_pattern")
        self.assertEqual(obs["category"], "linguistic")
        self.assertEqual(obs["method"], MULTI_SIGNAL_METHOD_ID)
        score = obs["confidence"]["score"]
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertEqual(obs["confidence"]["model_id"], MULTI_SIGNAL_METHOD_ID)
        self.assertTrue(obs["confidence"].get("version"))
        ev = obs["evidence"]
        self.assertIn("source_text", ev)
        self.assertIn("stuff", ev["source_text"])
        self.assertGreaterEqual(ev["hedge_count"], 1)
        self.assertGreaterEqual(ev["vague_count"], 1)
        self.assertGreaterEqual(ev["distancing_count"], 1)
        self.assertGreaterEqual(ev["families"], 2)
        self.assertIn("hedging", ev["inputs_used"])
        _assert_no_forbidden(self, pkg["observations"])

    def test_enabled_emits_nothing_on_clean_transcript(self):
        pkg = default_runner(enable_assisted=True).build_package(CLEAN)
        self.assertEqual(_assisted(pkg["observations"]), [])
        # ... and the baseline adapter alone also emits nothing on clean text.
        adapter = make_multi_signal_assisted_adapter()
        self.assertEqual(adapter(CLEAN).to_dicts(), [])

    def test_build_package_override_enables(self):
        pkg = default_runner().build_package(CONVERGING, enable_assisted=True)
        self.assertEqual(len(_assisted(pkg["observations"])), 1)
        pkg2 = default_runner(enable_assisted=True).build_package(CONVERGING, enable_assisted=False)
        self.assertEqual(_assisted(pkg2["observations"]), [])

    def test_registered_adapter_used_when_present(self):
        register_assisted_observer("multi_signal", make_multi_signal_assisted_adapter())
        res = run_assisted_observers(CONVERGING, enabled=True)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].to_dicts()[0]["label"], "multi_signal_language_pattern")

    def test_sealed_package_stays_observed_indicator(self):
        pkg = default_runner(enable_assisted=True).build_package(CONVERGING)
        sealed = seal_observation_package(pkg)
        self.assertEqual(sealed["epistemic_status"], "observed_indicator")
        self.assertFalse(sealed["is_definitive_finding"])
        _assert_no_forbidden(self, sealed["observations"])


class TestAssistedProvenance(unittest.TestCase):
    def setUp(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def tearDown(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def test_provenance_present_on_every_assisted_observation(self):
        pkg = default_runner(enable_assisted=True).build_package(CONVERGING)
        assisted = _assisted(pkg["observations"])
        self.assertTrue(assisted)
        for obs in assisted:
            ev = obs["evidence"]
            self.assertTrue(ev.get("assisted"))
            self.assertEqual(ev.get("adapter"), "multi_signal")
            self.assertEqual(ev.get("adapter_version"), "v1")
            self.assertEqual(ev.get("model_id"), MULTI_SIGNAL_METHOD_ID)
            prov = ev.get("assisted_provenance") or {}
            self.assertEqual(prov.get("adapter"), "multi_signal")
            self.assertEqual(prov.get("adapter_version"), "v1")
            self.assertEqual(prov.get("model_id"), MULTI_SIGNAL_METHOD_ID)
            self.assertEqual(prov.get("method"), MULTI_SIGNAL_METHOD_ID)
            self.assertTrue(prov.get("version"))
            self.assertTrue(prov.get("inputs_used"))
            self.assertIn("cueliez/multi_signal@v1", prov.get("provenance_model_id", ""))

    def test_protocol_observer_carries_its_provenance(self):
        prov = AssistedModelProvenance(provider="local", model="demo-model", version="v2", adapter_version="a3")

        class DemoObserver:
            method_id = "cueliez.observations.assisted.demo/v2"

            def __init__(self):
                self._prov = prov

            @property
            def provenance(self):
                return self._prov

            def observe(self, transcript):
                result = ObservationResult(method=self.method_id)
                result.observations.append(make_observation(
                    label="demo_indicator",
                    score=0.5,
                    method_id=self.method_id,
                    category="linguistic",
                    evidence={"source_text": "demo", "inputs_used": ["transcript"]},
                ))
                return result

        register_assisted_observer("demo", DemoObserver(), prov)
        res = run_assisted_observers(CONVERGING, enabled=True)
        self.assertEqual(len(res), 1)
        obs = res[0].to_dicts()[0]
        self.assertEqual(obs["evidence"]["assisted_provenance"]["provenance_model_id"], prov.model_id)
        self.assertEqual(obs["evidence"]["assisted_provenance"]["version"], "v2")
        # ... and it stays silent when disabled.
        self.assertEqual(run_assisted_observers(CONVERGING, enabled=False), [])


class TestAssistedVerdictShapedFiltering(unittest.TestCase):
    def setUp(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def tearDown(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def test_verdict_shaped_evidence_key_is_filtered(self):
        def bad_adapter(transcript):
            result = ObservationResult(method="cueliez.observations.assisted.bad/v1")
            result.observations.append(make_observation(
                label="multi_signal_language_pattern",
                score=0.9,
                method_id="cueliez.observations.assisted.bad/v1",
                category="linguistic",
                # Verdict-shaped key in evidence: must never reach output.
                evidence={"truth_score": 0.9, "source_text": "x"},
            ))
            return result

        register_assisted_observer("bad", bad_adapter)
        res = run_assisted_observers(CONVERGING, enabled=True)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].to_dicts(), [])
        self.assertTrue(any("assisted_verdict_shaped_filtered" in n for n in res[0].notes))
        merged = merge_assisted_observations([], CONVERGING, enabled=True)
        self.assertEqual(merged, [])
        _assert_no_forbidden(self, merged)

    def test_verdict_shaped_cue_text_is_filtered(self):
        def bad_adapter(transcript):
            result = ObservationResult(method="cueliez.observations.assisted.bad/v1")
            result.observations.append(make_observation(
                label="multi_signal_language_pattern",
                score=0.5,
                method_id="cueliez.observations.assisted.bad/v1",
                category="linguistic",
                evidence={"source_text": "x"},
                cue="This looks like the subject is guilty.",
            ))
            return result

        register_assisted_observer("bad", bad_adapter)
        self.assertEqual(merge_assisted_observations([], CONVERGING, enabled=True), [])

    def test_is_verdict_shaped_detector(self):
        self.assertTrue(is_verdict_shaped_observation({"label": "lying", "confidence": {"score": 0.5, "model_id": "m"}, "evidence": {}}))
        self.assertTrue(is_verdict_shaped_observation({"label": "ok", "confidence": {"score": 0.5, "model_id": "m"}, "evidence": {"deception_confirmed": True}}))
        self.assertFalse(is_verdict_shaped_observation({"label": "multi_signal_language_pattern", "confidence": {"score": 0.5, "model_id": "m"}, "evidence": {"source_text": "maybe stuff"}}))

    def test_adapter_raising_fails_closed(self):
        def boom(transcript):
            raise FileNotFoundError("local model weights absent")

        register_assisted_observer("boom", boom)
        self.assertEqual(run_assisted_observers(CONVERGING, enabled=True), [])
        # Rule-based observations are unaffected by the failed adapter.
        pkg = default_runner().build_package(CONVERGING)
        self.assertTrue(pkg["observations"])

    def test_mixed_good_and_bad_adapters_keep_only_good(self):
        def bad_adapter(transcript):
            result = ObservationResult(method="cueliez.observations.assisted.bad/v1")
            result.observations.append(make_observation(
                label="multi_signal_language_pattern", score=0.9,
                method_id="cueliez.observations.assisted.bad/v1", category="linguistic",
                evidence={"truth_score": 0.9},
            ))
            return result

        register_assisted_observer("bad", bad_adapter)
        register_assisted_observer("multi_signal", make_multi_signal_assisted_adapter())
        merged = merge_assisted_observations([], CONVERGING, enabled=True)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["label"], "multi_signal_language_pattern")
        _assert_no_forbidden(self, merged)


class TestAssistedRegistryAndObserver(unittest.TestCase):
    def setUp(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def tearDown(self):
        clear_assisted_registry()
        os.environ.pop("CUELIEZ_ASSISTED_OBSERVERS", None)

    def test_reregistering_same_name_replaces(self):
        calls = []

        def first(transcript):
            calls.append("first")
            return ObservationResult(method="cueliez.observations.assisted.first/v1")

        def second(transcript):
            calls.append("second")
            return ObservationResult(method="cueliez.observations.assisted.second/v1")

        register_assisted_observer("dup", first)
        register_assisted_observer("dup", second)
        run_assisted_observers(CONVERGING, enabled=True)
        self.assertEqual(calls, ["second"])

    def test_multi_signal_observer_object(self):
        obs = MultiSignalAssistedObserver()
        self.assertEqual(obs.method_id, MULTI_SIGNAL_METHOD_ID)
        self.assertEqual(obs.provenance.model, "multi_signal")
        res = obs.observe(CONVERGING)
        self.assertEqual(len(res.to_dicts()), 1)

    def test_default_runner_has_no_assisted_observer_in_list(self):
        for runner in (default_runner(), full_runner(), default_runner(enable_assisted=True)):
            ids = {getattr(o, "method_id", "") for o in runner.observers}
            self.assertFalse(any("assisted" in i for i in ids), ids)


class TestAssistedCliEndToEnd(unittest.TestCase):
    """Black-box check that the existing --enable-assisted flag works end
    to end (no CLI changes here; this only exercises it)."""

    def test_cli_enable_assisted_emits_multi_signal(self):
        repo = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env["PYTHONPATH"] = str(repo / "src")
        env.pop("CUELIEZ_ASSISTED_OBSERVERS", None)
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "t.json"
            transcript.write_text(json.dumps(CONVERGING), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-m", "cueliez", str(transcript),
                 "--enable-assisted", "--no-seal", "--print-json"],
                capture_output=True, text=True, env=env, cwd=str(repo), timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
            pkg = json.loads(proc.stdout[proc.stdout.index("{"):])
            assisted = _assisted(pkg.get("observations") or [])
            self.assertEqual(len(assisted), 1)
            self.assertEqual(assisted[0]["label"], "multi_signal_language_pattern")
            self.assertEqual(seal_observation_package(pkg)["epistemic_status"], "observed_indicator")
            _assert_no_forbidden(self, pkg["observations"])

    def test_cli_without_flag_emits_no_assisted(self):
        repo = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env["PYTHONPATH"] = str(repo / "src")
        env.pop("CUELIEZ_ASSISTED_OBSERVERS", None)
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "t.json"
            transcript.write_text(json.dumps(CONVERGING), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-m", "cueliez", str(transcript), "--no-seal", "--print-json"],
                capture_output=True, text=True, env=env, cwd=str(repo), timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
            pkg = json.loads(proc.stdout[proc.stdout.index("{"):])
            self.assertEqual(_assisted(pkg.get("observations") or []), [])


if __name__ == "__main__":
    unittest.main()
