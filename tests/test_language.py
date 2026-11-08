import pathlib
import re
import unittest

from cueliez.gates import BANNED_ANNOTATION_KEYS, DISCLAIMER, PROHIBITED_USES, seal_observation_package
from cueliez.memory import ALLOWED_GROUNDED_EPISTEMIC, FORBIDDEN_EPISTEMIC, MemoryEngine
from cueliez.observations.base import FORBIDDEN_LABELS, make_observation

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "cueliez"


class TestForbiddenVocabularies(unittest.TestCase):
    def test_base_forbidden_labels(self):
        for x in ("lying", "lie", "deception_confirmed", "guilty", "truthful", "deceptive"):
            self.assertIn(x, FORBIDDEN_LABELS)

    def test_memory_epistemic_boundaries(self):
        self.assertIn("observed_indicator", ALLOWED_GROUNDED_EPISTEMIC)
        for x in ("legal_finding", "diagnosis", "deception_confirmed", "verdict", "guilty", "lie"):
            self.assertIn(x, FORBIDDEN_EPISTEMIC)
        self.assertTrue(ALLOWED_GROUNDED_EPISTEMIC.isdisjoint(FORBIDDEN_EPISTEMIC))

    def test_gate_bans_align_with_language_rules(self):
        # annotations that would store definitive claims
        self.assertIn("deception_confirmed", BANNED_ANNOTATION_KEYS)
        self.assertIn("is_lying", BANNED_ANNOTATION_KEYS)
        self.assertIn("truth_score", BANNED_ANNOTATION_KEYS)
        self.assertIn("polygraph_substitute", PROHIBITED_USES)
        self.assertIn("lie_detector_claim", PROHIBITED_USES)


class TestVerdictRejectionBase(unittest.TestCase):
    def test_make_observation_rejects_verdict_labels(self):
        for label in FORBIDDEN_LABELS:
            with self.assertRaises(ValueError):
                make_observation(label=label, score=0.5, method_id="m/v1", category="linguistic")

    def test_make_observation_allows_neutral_labels(self):
        o = make_observation(label="hedging_language_present", score=0.5, method_id="m/v1", category="linguistic")
        self.assertEqual(o.to_dict()["label"], "hedging_language_present")


class TestVerdictRejectionGates(unittest.TestCase):
    def _pkg(self, obs):
        return {"observations": obs}

    def test_rejects_verdict_observation_labels(self):
        for label in ("lying", "deception_confirmed", "guilty", "truthful"):
            obs = {"label": label, "confidence": {"score": 0.9, "model_id": "x/v1"}}
            with self.assertRaises(Exception) as ctx:
                seal_observation_package(self._pkg([obs]))
            self.assertEqual(getattr(ctx.exception, "code", None), "verdict_language", label)

    def test_rejects_claim_field_verdict(self):
        obs = {"claim": "lying", "confidence": {"score": 0.9, "model_id": "x/v1"}}
        with self.assertRaises(Exception) as ctx:
            seal_observation_package(self._pkg([obs]))
        self.assertEqual(ctx.exception.code, "verdict_language")

    def test_rejects_definitive_package_markers(self):
        with self.assertRaises(Exception):
            seal_observation_package({"is_definitive_finding": True})
        with self.assertRaises(Exception):
            seal_observation_package({"epistemic_status": "diagnosis"})
        with self.assertRaises(Exception):
            seal_observation_package({"epistemic_status": "legal_finding"})

    def test_seal_forces_safe_fields(self):
        out = seal_observation_package({"observations": [], "epistemic_status": "anything", "is_definitive_finding": "no"})
        self.assertEqual(out["epistemic_status"], "observed_indicator")
        self.assertEqual(out["origin"], "grounded")
        self.assertIs(out["is_definitive_finding"], False)
        self.assertIn("not a lie detector", out["disclaimer"].lower())


class TestVerdictRejectionMemory(unittest.TestCase):
    def test_rejects_forbidden_epistemic(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(store_path=td)
            for status in FORBIDDEN_EPISTEMIC:
                with self.assertRaises(Exception):
                    m.remember_observation("x", epistemic_status=status)

    def test_rejects_unknown_grounded_epistemic(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(store_path=td)
            with self.assertRaises(Exception):
                m.remember_observation("x", epistemic_status="fact")

    def test_seal_package_requires_hardened_fields(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            m = MemoryEngine(store_path=td)
            with self.assertRaises(Exception):
                m.seal_package({"epistemic_status": "observed_indicator", "origin": "grounded", "disclaimer": "d", "firewall": {"contamination_check": "passed"}})
            # missing is_definitive_finding False check is fine if absent? code rejects only True; but firewall/disclaimer required.
            ok = {
                "epistemic_status": "observed_indicator", "origin": "grounded",
                "is_definitive_finding": False, "disclaimer": DISCLAIMER,
                "firewall": {"contamination_check": "passed"}, "observations": [],
                "package_hash": "a" * 64,
            }
            sid = m.seal_package(ok)
            self.assertTrue(sid)


class TestSourceLanguageScan(unittest.TestCase):
    """Strict static checks: code must not market/detect lies; bans must remain present."""

    def _py_files(self):
        return list(SRC.rglob("*.py"))

    def test_no_lie_detection_claims_in_code(self):
        # Allowed contexts: disclaimers, ban lists, comparisons, comments stating "not a lie detector"/"never lie detection".
        forbidden_claims = [
            r"\bdetects?\s+lies\b",
            r"\blie\s+detection\s+engine\b",
            r"\btruth\s+detector\b",
            r"\bconfirms?\s+(?:lying|deception)\b",
            r"\bsubject\s+is\s+lying\b",
        ]
        for path in self._py_files():
            text = path.read_text(encoding="utf-8")
            for pat in forbidden_claims:
                m = re.search(pat, text, re.I)
                self.assertIsNone(m, f"Forbidden claim {pat!r} in {path}: {m.group(0) if m else ''}")

    def test_disclaimer_and_ban_strings_present(self):
        gates = (SRC / "gates.py").read_text(encoding="utf-8")
        self.assertIn("not a lie detector", gates.lower())
        self.assertIn("lie_detector_claim", gates)
        self.assertIn("polygraph_substitute", gates)
        base = (SRC / "observations" / "base.py").read_text(encoding="utf-8")
        self.assertIn("Forbidden verdict label", base)

    def test_observation_modules_have_non_verdict_docstring(self):
        for name in ("linguistic.py", "consistency.py", "behavioral.py", "prosody.py", "visual.py", "physiological.py", "multimodal.py"):
            text = (SRC / "observations" / name).read_text(encoding="utf-8").lower()
            ok = bool(re.search(r"not\s+verdicts?|never\s+.*verdict|not\s+(?:a\s+)?(?:medical\s+)?(?:or\s+)?(?:deception\s+)?determination|not\s+deception\s+determinations?|never\s+produce\s+deception", text))
            self.assertTrue(ok, f"{name} missing non-verdict framing")


if __name__ == "__main__":
    unittest.main()
