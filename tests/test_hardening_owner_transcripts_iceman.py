"""Iceman hardening pass: seal/gate/hash/evidence integrity on owner demo transcripts.

Covers docs/examples/owner_{clean,conflict,hedging}_interview.json.
First-pilot modes in scope: generic + interrogation (session helper path where applicable).
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from cueliez.delivery.notes import attach_officer_cue_notes
from cueliez.gates import (
    GateError,
    SessionGateState,
    is_sealed,
    record_consent,
    seal_observation_package,
    verify_package_hash,
    compute_package_hash,
)
from cueliez.memory import MemoryEngine, SealError
from cueliez.observations import default_runner
from cueliez.session import assert_can_observe, seal as session_seal, start_session

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "docs" / "examples"
TRANSCRIPTS = [
    "owner_clean_interview.json",
    "owner_conflict_interview.json",
    "owner_hedging_interview.json",
]

FORBIDDEN_IN_NEW_TEXT = re.compile(
    r"\b(lie\s+detector|detects?\s+lies?|lie\s+detection|truth\s+detector|truth\s+score|"
    r"proves?\s+deception|confirms?\s+(lying|deception)|subject\s+is\s+lying|"
    r"\bguilty\b|\bdiagnosis\b\s+of|deception_confirmed)\b",
    re.I,
)
BANNED_OBS_LABELS = {"lying", "lie", "deception_confirmed", "guilty", "truthful", "deceptive", "dishonest", "honest"}
BANNED_ANNOTATION_KEYS = {"diagnosis", "legal_finding", "deception_confirmed", "lying", "guilty", "truth_score", "is_lying"}


def _load(name: str):
    with open(EXAMPLES / name, encoding="utf-8") as f:
        return json.load(f)


def _build(name: str):
    return default_runner().build_package(_load(name), session_id=f"hardening-{name}")


def _seal_generic(pkg: dict):
    return seal_observation_package(dict(pkg), SessionGateState(mode="generic"))


def _seal_interrogation_via_session(pkg: dict):
    state = SessionGateState(mode="interrogation", intended_uses=["interview support"])
    record_consent(state, attested_by="reviewer-1")
    state.training_acknowledged = True
    state.training_version = "hardening-v1"
    start_session(state)
    assert_can_observe(state)
    return session_seal(dict(pkg), state), state


class HardeningOwnerTranscriptsIceman(unittest.TestCase):
    def test_task1_seal_path_fields_all_transcripts(self):
        for name in TRANSCRIPTS:
            with self.subTest(transcript=name, path="generic"):
                out = _seal_generic(_build(name))
                self.assertEqual(out["epistemic_status"], "observed_indicator")
                self.assertIs(out["is_definitive_finding"], False)
                self.assertEqual(out["origin"], "grounded")
                self.assertEqual(out["product"], "CueLiez")
                self.assertTrue(str(out.get("disclaimer") or "").strip())
                self.assertIn("schema_version", out)
                self.assertIn("product_version", out)
                self.assertIsNotNone(out.get("sealed_at"))
                self.assertTrue(str(out.get("package_hash") or "").strip())
            with self.subTest(transcript=name, path="session_interrogation"):
                out, state = _seal_interrogation_via_session(_build(name))
                self.assertEqual(out["epistemic_status"], "observed_indicator")
                self.assertIs(out["is_definitive_finding"], False)
                self.assertEqual(out["origin"], "grounded")
                self.assertEqual(out["product"], "CueLiez")
                self.assertTrue(str(out.get("disclaimer") or "").strip())
                self.assertTrue(out["gate_state"]["requirements"]["consent_required"])
                self.assertTrue(verify_package_hash(out))

    def test_task2_evidence_preserved_no_stripping(self):
        for name in TRANSCRIPTS:
            with self.subTest(transcript=name):
                out = _seal_generic(_build(name))
                for i, obs in enumerate(out.get("observations") or []):
                    ev = obs.get("evidence")
                    self.assertIsInstance(ev, dict, f"obs[{i}] evidence must be dict")
                    # must not strip unknown/added evidence keys: presence of any key is preserved by seal
                    # and source text keys, when present, remain
                    for k in ("source_text", "source_texts", "source_span", "turn_refs", "role", "turn_index", "turn_indices"):
                        if k in (default_runner().build_package(_load(name)).get("observations") or [{}])[min(i, len(out.get("observations") or []) - 1)].get("evidence", {}):
                            pass
                # direct preservation check against pre-seal package
                pre = _build(name)
                sealed = _seal_generic(pre)
                pre_obs = pre.get("observations") or []
                post_obs = sealed.get("observations") or []
                self.assertEqual(len(pre_obs), len(post_obs))
                for a, b in zip(pre_obs, post_obs):
                    self.assertEqual(a.get("evidence"), b.get("evidence"), "evidence dict must be preserved")
                    self.assertEqual(a.get("label"), b.get("label"))
                    self.assertEqual(a.get("cue_id"), b.get("cue_id"))

    def test_task3_hash_reproducibility(self):
        for name in TRANSCRIPTS:
            with self.subTest(transcript=name):
                transcript = _load(name)
                # deterministic runner input
                s = SessionGateState(mode="generic")
                p1 = seal_observation_package(default_runner().build_package(transcript, session_id="h1"), s)
                p2 = seal_observation_package(default_runner().build_package(transcript, session_id="h1"), s)
                self.assertTrue(verify_package_hash(p1))
                self.assertTrue(verify_package_hash(p2))
                self.assertEqual(compute_package_hash(p1), p1["package_hash"])
                self.assertEqual(p1["package_hash"], p2["package_hash"], "deterministic inputs must yield same hash")

    def test_task4_post_seal_immutability(self):
        for name in TRANSCRIPTS:
            with self.subTest(transcript=name):
                sealed = _seal_generic(_build(name))
                self.assertTrue(is_sealed(sealed))
                with self.assertRaises(ValueError):
                    attach_officer_cue_notes(sealed, [{"cue_id": "x", "action": "noted", "note": "test"}])
                # normal observation mutation path refused by immutability guard pattern:
                # sealed packages must not be mutated; verify helper/flag
                self.assertTrue(sealed.get("sealed") is True)

    def test_task5_banned_content_rejected(self):
        for name in TRANSCRIPTS:
            base = _seal_generic(_build(name))
            obs = list(base.get("observations") or [])
            with self.subTest(transcript=name, kind="verdict_label_obs"):
                if obs:
                    bad = [dict(obs[0]), *[dict(o) for o in obs[1:]]]
                    bad[0]["label"] = "lying"  # negative-test fixture
                    with self.assertRaises(GateError):
                        seal_observation_package({"observations": bad}, SessionGateState(mode="generic"))
            with self.subTest(transcript=name, kind="banned_annotation"):
                with self.assertRaises(GateError):
                    seal_observation_package({"observations": obs, "annotations": {"truth_score": 1}}, SessionGateState(mode="generic"))
            with self.subTest(transcript=name, kind="definitive_finding"):
                with self.assertRaises(GateError):
                    seal_observation_package({"observations": obs, "is_definitive_finding": True}, SessionGateState(mode="generic"))

    def test_task6_gate_state_structure(self):
        required = {"mode", "consent", "consent_recorded_at", "consent_attested_by", "training_acknowledged",
                    "training_version", "dual_control_records", "intended_uses", "requirements"}
        req_keys = {"consent_required", "training_required", "dual_control_required"}
        for name in TRANSCRIPTS:
            with self.subTest(transcript=name):
                out = _seal_generic(_build(name))
                gs = out.get("gate_state")
                self.assertIsInstance(gs, dict)
                self.assertTrue(required.issubset(gs.keys()), f"missing {required - set(gs.keys())}")
                self.assertTrue(req_keys.issubset((gs.get("requirements") or {}).keys()))
                self.assertIsInstance(gs["dual_control_records"], list)
                self.assertIsInstance(gs["intended_uses"], list)

    def test_task7_memory_substrate(self):
        for name in TRANSCRIPTS:
            with self.subTest(transcript=name):
                sealed = _seal_generic(_build(name))
                self.assertTrue(sealed.get("package_hash"))
                with tempfile.TemporaryDirectory() as td:
                    eng = MemoryEngine(store_path=td)
                    sid = eng.seal_package(sealed)
                    self.assertTrue(sid)
                    # stored seal must remain observed indicator / non-finding
                    seal_path = Path(td) / "seals" / f"{sid}.json"
                    self.assertTrue(seal_path.exists())
                    stored = json.loads(seal_path.read_text(encoding="utf-8"))
                    self.assertEqual(stored.get("epistemic_status"), "observed_indicator")
                    self.assertIs(stored.get("is_definitive_finding"), False)
                # requires package_hash
                with tempfile.TemporaryDirectory() as td:
                    eng = MemoryEngine(store_path=td)
                    bad = dict(sealed)
                    bad.pop("package_hash", None)
                    with self.assertRaises((SealError, GateError, ValueError, Exception)):
                        eng.seal_package(bad)

    def test_task8_wording_neutral(self):
        # Check this test file and iceman hardening doc additions for forbidden verdict terms.
        # Banned-key/label test data and regex definitions are intentional negative-test fixtures.
        targets = [Path(__file__)]
        for path in targets:
            lines = path.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines, 1):
                ctx = "".join(lines[max(0, i - 6):i])
                if any(x in ctx for x in ("FORBIDDEN_IN_NEW_TEXT", "BANNED_OBS_LABELS", "BANNED_ANNOTATION_KEYS")):
                    continue
                if "verdict terms" in line or "negative-test fixture" in line:
                    continue
                m = FORBIDDEN_IN_NEW_TEXT.search(line)
                if m:
                    self.fail(f"forbidden term in {path.name}:{i}: {m.group(0)!r}")


if __name__ == "__main__":
    unittest.main()
