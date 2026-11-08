import unittest

from cueliez.gates import (
    BANNED_ANNOTATION_KEYS,
    CONSENT_REQUIRED_MODES,
    DISCLAIMER,
    DUAL_CONTROL_MODES,
    PROHIBITED_USES,
    TRAINING_REQUIRED_MODES,
    DualControlRecord,
    GateError,
    SessionGateState,
    check_prohibited_uses,
    record_consent,
    record_dual_acknowledge,
    require_consent,
    require_dual_control_for_seal,
    require_training,
    seal_observation_package,
)


class TestGatePolicyConstants(unittest.TestCase):
    def test_consent_required_modes(self):
        self.assertEqual(CONSENT_REQUIRED_MODES, frozenset({"interrogation", "therapy", "clinical", "government"}))

    def test_dual_control_modes(self):
        self.assertEqual(DUAL_CONTROL_MODES, frozenset({"government"}))

    def test_training_required_modes(self):
        self.assertEqual(TRAINING_REQUIRED_MODES, frozenset({"interrogation", "therapy", "clinical", "government"}))

    def test_prohibited_uses_include_core_bans(self):
        for key in ("automated_detention", "automated_charge", "definitive_deception_claim",
                    "clinical_diagnosis", "polygraph_substitute", "lie_detector_claim"):
            self.assertIn(key, PROHIBITED_USES)

    def test_disclaimer_language(self):
        d = DISCLAIMER.lower()
        self.assertIn("probabilistic observations", d)
        self.assertIn("not a lie detector", d)
        self.assertIn("not a medical device", d)
        self.assertNotIn("detects lies", d)

    def test_banned_annotation_keys_cover_verdicts(self):
        for k in ("diagnosis", "legal_finding", "deception_confirmed", "lying", "guilty", "truth_score", "polygraph_result"):
            self.assertIn(k, BANNED_ANNOTATION_KEYS)


class TestSessionGateState(unittest.TestCase):
    def test_generic_no_consent_training_dual_required(self):
        s = SessionGateState(mode="generic")
        self.assertFalse(s.requires_consent())
        self.assertFalse(s.requires_training())
        self.assertFalse(s.requires_dual_control())
        self.assertTrue(s.consent_ok())

    def test_high_stakes_requirements(self):
        for mode in CONSENT_REQUIRED_MODES:
            s = SessionGateState(mode=mode)
            self.assertTrue(s.requires_consent())
            self.assertTrue(s.requires_training())
        self.assertTrue(SessionGateState(mode="government").requires_dual_control())
        self.assertFalse(SessionGateState(mode="interrogation").requires_dual_control())

    def test_consent_ok_strict(self):
        s = SessionGateState(mode="interrogation", consent=True, consent_recorded_at=1.0, consent_attested_by="off1")
        self.assertTrue(s.consent_ok())
        s.consent_attested_by = "   "
        self.assertFalse(s.consent_ok())
        s.consent_attested_by = None
        self.assertFalse(s.consent_ok())
        s.consent_attested_by = "off1"
        s.consent = False
        self.assertFalse(s.consent_ok())
        s.consent = True
        s.consent_recorded_at = None
        self.assertFalse(s.consent_ok())


class TestConsent(unittest.TestCase):
    def test_record_consent_success(self):
        s = SessionGateState(mode="interrogation")
        record_consent(s, attested_by="officer-a", subject_id="sub1", jurisdiction="CA")
        self.assertTrue(s.consent)
        self.assertIsNotNone(s.consent_recorded_at)
        self.assertEqual(s.consent_attested_by, "officer-a")
        self.assertEqual(s.subject_id, "sub1")
        self.assertEqual(s.jurisdiction, "CA")

    def test_record_consent_requires_attester(self):
        s = SessionGateState(mode="interrogation")
        for bad in ("", "   ", None):
            with self.assertRaises(GateError) as ctx:
                record_consent(s, attested_by=bad)  # type: ignore[arg-type]
            self.assertEqual(ctx.exception.code, "consent_attester_required")

    def test_require_consent_blocks_unconsented(self):
        s = SessionGateState(mode="clinical")
        with self.assertRaises(GateError) as ctx:
            require_consent(s, action="start")
        self.assertEqual(ctx.exception.code, "consent_required")
        self.assertIn("before start", ctx.exception.message)
        self.assertIn("consent", ctx.exception.message.lower())

    def test_require_consent_passes_generic(self):
        require_consent(SessionGateState(mode="generic"))

    def test_require_consent_passes_when_recorded(self):
        s = SessionGateState(mode="therapy")
        record_consent(s, attested_by="clin1")
        require_consent(s, action="seal")


class TestTraining(unittest.TestCase):
    def test_training_required(self):
        s = SessionGateState(mode="interrogation")
        with self.assertRaises(GateError) as ctx:
            require_training(s)
        self.assertEqual(ctx.exception.code, "training_required")

    def test_training_version_required(self):
        s = SessionGateState(mode="government", training_acknowledged=True, training_version="  ")
        with self.assertRaises(GateError) as ctx:
            require_training(s)
        self.assertEqual(ctx.exception.code, "training_version_required")

    def test_training_ok(self):
        s = SessionGateState(mode="clinical", training_acknowledged=True, training_version="t-2026.1")
        require_training(s)

    def test_training_not_required_generic(self):
        require_training(SessionGateState(mode="generic"))


class TestDualControl(unittest.TestCase):
    def test_record_dual_acknowledge(self):
        s = SessionGateState(mode="government")
        rec = record_dual_acknowledge(s, "cue1", "off-a", "off-b", "reviewed")
        self.assertIsInstance(rec, DualControlRecord)
        self.assertEqual(len(s.dual_control_records), 1)
        self.assertEqual(rec.cue_id, "cue1")

    def test_dual_control_not_applicable(self):
        s = SessionGateState(mode="interrogation")
        with self.assertRaises(GateError) as ctx:
            record_dual_acknowledge(s, "c", "a", "b")
        self.assertEqual(ctx.exception.code, "dual_control_not_applicable")

    def test_dual_control_ids_required(self):
        s = SessionGateState(mode="government")
        with self.assertRaises(GateError) as ctx:
            record_dual_acknowledge(s, "c", "", "b")
        self.assertEqual(ctx.exception.code, "dual_control_ids_required")

    def test_dual_control_same_officer(self):
        s = SessionGateState(mode="government")
        with self.assertRaises(GateError) as ctx:
            record_dual_acknowledge(s, "c", "same", "same")
        self.assertEqual(ctx.exception.code, "dual_control_same_officer")

    def test_dual_control_seal_incomplete(self):
        s = SessionGateState(mode="government")
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        with self.assertRaises(GateError) as ctx:
            require_dual_control_for_seal(s, ["cue1", "cue2"])
        self.assertEqual(ctx.exception.code, "dual_control_incomplete")
        record_dual_acknowledge(s, "cue1", "a", "b")
        with self.assertRaises(GateError):
            require_dual_control_for_seal(s, ["cue1", "cue2"])
        record_dual_acknowledge(s, "cue2", "c", "d")
        require_dual_control_for_seal(s, ["cue1", "cue2"])

    def test_dual_control_not_needed_when_no_high_priority(self):
        s = SessionGateState(mode="government")
        require_dual_control_for_seal(s, [])


class TestProhibitedUses(unittest.TestCase):
    def test_prohibited_use_rejected(self):
        with self.assertRaises(GateError) as ctx:
            check_prohibited_uses(["automated detention"])
        self.assertEqual(ctx.exception.code, "prohibited_use")
        with self.assertRaises(GateError):
            check_prohibited_uses(["lie_detector_claim"])
        with self.assertRaises(GateError):
            check_prohibited_uses(["POLYGRAPH SUBSTITUTE"])

    def test_allowed_uses_pass(self):
        check_prohibited_uses(None)
        check_prohibited_uses([])
        check_prohibited_uses(["interview support", "supervisor_review"])


def _valid_obs(label="hesitation_marker_present", score=0.5, model_id="m/v1", method="m/v1", category="behavioral"):
    return {"label": label, "confidence": {"score": score, "model_id": model_id}, "evidence": {}, "method": method, "category": category}


class TestSealObservationPackage(unittest.TestCase):
    def test_seal_minimal_success(self):
        out = seal_observation_package({"observations": [_valid_obs()]})
        self.assertEqual(out["epistemic_status"], "observed_indicator")
        self.assertEqual(out["origin"], "grounded")
        self.assertFalse(out["is_definitive_finding"])
        self.assertEqual(out["product"], "CueLiez")
        self.assertEqual(out["disclaimer"], DISCLAIMER)
        self.assertIn("sealed_at", out)
        self.assertEqual(out["firewall"]["contamination_check"], "passed")

    def test_seal_rejects_non_dict(self):
        with self.assertRaises(GateError) as ctx:
            seal_observation_package([])  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "seal_invalid")

    def test_seal_rejects_definitive_finding_flag(self):
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"is_definitive_finding": True})
        self.assertEqual(ctx.exception.code, "definitive_finding_forbidden")

    def test_seal_rejects_forbidden_epistemic_status(self):
        for status in ("fact_finding", "legal_finding", "diagnosis", "deception_confirmed"):
            with self.assertRaises(GateError) as ctx:
                seal_observation_package({"epistemic_status": status})
            self.assertEqual(ctx.exception.code, "epistemic_status_forbidden", status)

    def test_seal_rejects_banned_annotations(self):
        for key in ("diagnosis", "lying", "guilty", "truth_score", "polygraph_result"):
            with self.assertRaises(GateError) as ctx:
                seal_observation_package({"annotations": {key: "x"}})
            self.assertEqual(ctx.exception.code, "contamination_attempt", key)

    def test_seal_rejects_invalid_annotations_type(self):
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"annotations": []})
        self.assertEqual(ctx.exception.code, "annotations_invalid")

    def test_seal_rejects_verdict_labels(self):
        for label in ("lying", "lie", "deception_confirmed", "guilty", "truthful"):
            with self.assertRaises(GateError) as ctx:
                seal_observation_package({"observations": [_valid_obs(label=label)]})
            self.assertEqual(ctx.exception.code, "verdict_language", label)

    def test_seal_rejects_missing_confidence(self):
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [{"label": "x", "method": "m", "category": "c"}]})
        self.assertEqual(ctx.exception.code, "missing_confidence")
        with self.assertRaises(GateError):
            seal_observation_package({"observations": [{"label": "x", "confidence": {"model_id": "m"}, "method": "m", "category": "c"}]})

    def test_seal_rejects_bad_score(self):
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [_valid_obs(score=1.5)]})
        self.assertEqual(ctx.exception.code, "confidence_out_of_range")
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [_valid_obs(score=-0.1)]})
        self.assertEqual(ctx.exception.code, "confidence_out_of_range")
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [{"label": "x", "confidence": {"score": "no", "model_id": "m"}, "method": "m", "category": "c"}]})
        self.assertEqual(ctx.exception.code, "invalid_confidence_score")

    def test_seal_rejects_missing_model_id(self):
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [{"label": "x", "confidence": {"score": 0.5, "model_id": ""}, "method": "m", "category": "c"}]})
        self.assertEqual(ctx.exception.code, "missing_model_id")

    def test_seal_rejects_invalid_observation_shape(self):
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": ["bad"]})
        self.assertEqual(ctx.exception.code, "observation_invalid")
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": {}})
        self.assertEqual(ctx.exception.code, "observations_invalid")

    def test_seal_canonicalizes_detections(self):
        out = seal_observation_package({"detections": [_valid_obs()]})
        self.assertIn("observations", out)
        self.assertNotIn("detections", out)
        self.assertEqual(len(out["observations"]), 1)

    def test_seal_with_state_enforces_all_gates(self):
        s = SessionGateState(mode="government", intended_uses=["interview support"])
        with self.assertRaises(GateError):
            seal_observation_package({"observations": [_valid_obs()]}, s, high_priority_cue_ids=["c1"])
        record_consent(s, attested_by="off")
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [_valid_obs()]}, s, high_priority_cue_ids=["c1"])
        self.assertEqual(ctx.exception.code, "training_required")
        s.training_acknowledged = True
        s.training_version = "v1"
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [_valid_obs()]}, s, high_priority_cue_ids=["c1"])
        self.assertEqual(ctx.exception.code, "dual_control_incomplete")
        record_dual_acknowledge(s, "c1", "a", "b")
        out = seal_observation_package({"observations": [_valid_obs()]}, s, high_priority_cue_ids=["c1"])
        self.assertTrue(out["firewall"]["consent_rechecked"])
        self.assertTrue(out["firewall"]["training_rechecked"])

    def test_seal_with_state_blocks_prohibited_use(self):
        s = SessionGateState(mode="interrogation", intended_uses=["lie_detector_claim"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": []}, s)
        self.assertEqual(ctx.exception.code, "prohibited_use")

    def test_generic_mode_seals_without_consent_state(self):
        s = SessionGateState(mode="generic")
        out = seal_observation_package({"observations": [_valid_obs()]}, s)
        self.assertFalse(out["firewall"]["consent_rechecked"])


class TestGateStateCapture(unittest.TestCase):
    def test_full_gate_state_serialized_in_package(self):
        s = SessionGateState(
            mode="government",
            intended_uses=["interview support", "supervisor_review"],
            subject_id="sub-1",
            jurisdiction="CA",
            operator_id="op-1",
        )
        record_consent(s, attested_by="officer-1", subject_id="sub-1", jurisdiction="CA")
        s.training_acknowledged = True
        s.training_version = "train-2026.1"
        record_dual_acknowledge(s, "cue-a", "off-a", "off-b", "reviewed")
        out = seal_observation_package({"observations": [_valid_obs()]}, s, high_priority_cue_ids=["cue-a"])

        self.assertIn("gate_state", out)
        gs = out["gate_state"]
        self.assertEqual(gs["mode"], "government")
        self.assertTrue(gs["consent"])
        self.assertEqual(gs["consent_attested_by"], "officer-1")
        self.assertIsNotNone(gs["consent_recorded_at"])
        self.assertEqual(gs["training_version"], "train-2026.1")
        self.assertTrue(gs["training_acknowledged"])
        self.assertEqual(gs["intended_uses"], ["interview support", "supervisor_review"])
        self.assertEqual(gs["subject_id"], "sub-1")
        self.assertEqual(gs["jurisdiction"], "CA")
        self.assertEqual(gs["operator_id"], "op-1")
        self.assertEqual(len(gs["dual_control_records"]), 1)
        dcr = gs["dual_control_records"][0]
        self.assertEqual(dcr["cue_id"], "cue-a")
        self.assertEqual(dcr["first_officer_id"], "off-a")
        self.assertEqual(dcr["second_officer_id"], "off-b")
        self.assertIn("acknowledged_at", dcr)
        self.assertEqual(dcr["notes"], "reviewed")
        self.assertTrue(gs["requirements"]["consent_required"])
        self.assertTrue(gs["requirements"]["training_required"])
        self.assertTrue(gs["requirements"]["dual_control_required"])

    def test_generic_state_captured_when_no_state_provided(self):
        out = seal_observation_package({"observations": [_valid_obs()]})
        gs = out["gate_state"]
        self.assertEqual(gs["mode"], "generic")
        self.assertFalse(gs["requirements"]["consent_required"])
        self.assertFalse(gs["requirements"]["training_required"])
        self.assertFalse(gs["requirements"]["dual_control_required"])
        self.assertTrue(out["firewall"]["gate_state_captured"])

    def test_session_gate_state_to_dict_is_self_describing(self):
        s = SessionGateState(mode="interrogation", consent=True, consent_recorded_at=123.0,
                             consent_attested_by="x", training_acknowledged=True, training_version="v")
        d = s.to_dict()
        for k in ("mode", "consent", "consent_recorded_at", "consent_attested_by", "dual_control_records",
                  "intended_uses", "training_acknowledged", "training_version", "requirements"):
            self.assertIn(k, d)


class TestPackageIntegrity(unittest.TestCase):
    def test_forced_epistemic_fields_and_disclaimer(self):
        out = seal_observation_package({"observations": [_valid_obs()], "epistemic_status": "x", "is_definitive_finding": "y"})
        self.assertEqual(out["epistemic_status"], "observed_indicator")
        self.assertFalse(out["is_definitive_finding"])
        self.assertEqual(out["origin"], "grounded")
        self.assertEqual(out["product"], "CueLiez")
        self.assertIn("product_version", out)
        self.assertIn("schema_version", out)
        self.assertEqual(out["disclaimer"], DISCLAIMER)
        self.assertIn("sealed_at", out)

    def test_hash_present_and_stable_for_identical_input(self):
        state = SessionGateState(mode="interrogation", consent=True, consent_recorded_at=1000.0,
                                 consent_attested_by="off", training_acknowledged=True, training_version="v1",
                                 intended_uses=["interview support"])
        pkg1 = {"observations": [_valid_obs(label="x", score=0.3, model_id="m/v1", method="m/v1", category="c")], "annotations": {"note": "ok"}}
        pkg2 = {"observations": [_valid_obs(label="x", score=0.3, model_id="m/v1", method="m/v1", category="c")], "annotations": {"note": "ok"}}
        out1 = seal_observation_package(pkg1, state)
        out2 = seal_observation_package(pkg2, state)
        self.assertIn("package_hash", out1)
        self.assertRegex(out1["package_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(out1["package_hash"], out2["package_hash"])
        # sealed_at differs (time), hash must not
        # (if test runs fast they might equal; hash stability is the requirement)
        self.assertEqual(out1["package_hash"], out2["package_hash"])

    def test_hash_changes_when_content_changes(self):
        state = SessionGateState(mode="generic")
        a = seal_observation_package({"observations": [_valid_obs(score=0.1)]}, state)
        b = seal_observation_package({"observations": [_valid_obs(score=0.2)]}, state)
        self.assertNotEqual(a["package_hash"], b["package_hash"])


class TestObservationContractEnforcement(unittest.TestCase):
    def test_missing_method_rejected(self):
        obs = {"label": "x", "confidence": {"score": 0.5, "model_id": "m"}, "category": "c"}
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [obs]})
        self.assertEqual(ctx.exception.code, "missing_method")

    def test_missing_category_rejected(self):
        obs = {"label": "x", "confidence": {"score": 0.5, "model_id": "m"}, "method": "m"}
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [obs]})
        self.assertEqual(ctx.exception.code, "missing_category")

    def test_missing_label_rejected(self):
        obs = {"label": "", "confidence": {"score": 0.5, "model_id": "m"}, "method": "m", "category": "c"}
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [obs]})
        self.assertEqual(ctx.exception.code, "missing_label")


class TestFailClosedHighStakes(unittest.TestCase):
    def _ready_state(self, mode):
        s = SessionGateState(mode=mode, intended_uses=["interview support"])
        record_consent(s, attested_by="attester")
        s.training_acknowledged = True
        s.training_version = "v1"
        return s

    def test_missing_consent_blocks_all_high_stakes_modes(self):
        for mode in ("interrogation", "therapy", "clinical", "government"):
            s = SessionGateState(mode=mode, training_acknowledged=True, training_version="v1")
            with self.assertRaises(GateError) as ctx:
                seal_observation_package({"observations": [_valid_obs()]}, s)
            self.assertEqual(ctx.exception.code, "consent_required", mode)

    def test_missing_training_blocks_all_high_stakes_modes(self):
        for mode in ("interrogation", "therapy", "clinical", "government"):
            s = SessionGateState(mode=mode)
            record_consent(s, attested_by="a")
            with self.assertRaises(GateError) as ctx:
                seal_observation_package({"observations": [_valid_obs()]}, s)
            self.assertEqual(ctx.exception.code, "training_required", mode)

    def test_missing_dual_control_blocks_government_high_priority(self):
        s = self._ready_state("government")
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [_valid_obs()]}, s, high_priority_cue_ids=["hp1"])
        self.assertEqual(ctx.exception.code, "dual_control_incomplete")

    def test_high_stakes_seals_when_all_gates_satisfied(self):
        for mode in ("interrogation", "therapy", "clinical"):
            s = self._ready_state(mode)
            out = seal_observation_package({"observations": [_valid_obs()]}, s)
            self.assertEqual(out["gate_state"]["mode"], mode)
            self.assertTrue(out["gate_state"]["consent"])
        s = self._ready_state("government")
        record_dual_acknowledge(s, "hp1", "a", "b")
        out = seal_observation_package({"observations": [_valid_obs()]}, s, high_priority_cue_ids=["hp1"])
        self.assertEqual(out["gate_state"]["mode"], "government")


class TestExportPath(unittest.TestCase):
    def test_export_returns_structured_json_with_gates_and_observations(self):
        import json
        from cueliez.gates import export_sealed_package_json
        s = self_ready = SessionGateState(mode="interrogation", intended_uses=["interview support"])
        record_consent(s, attested_by="off")
        s.training_acknowledged = True
        s.training_version = "v1"
        sealed = seal_observation_package({"observations": [_valid_obs()]}, s)
        text = export_sealed_package_json(sealed)
        data = json.loads(text)
        self.assertIn("observations", data)
        self.assertIn("gate_state", data)
        self.assertEqual(data["gate_state"]["mode"], "interrogation")
        self.assertEqual(data["epistemic_status"], "observed_indicator")
        # no system-decided claims in structure keys we control
        self.assertNotIn("lying", json.dumps(data).lower())

    def test_export_rejects_unsealed(self):
        from cueliez.gates import export_sealed_package_json
        with self.assertRaises(GateError):
            export_sealed_package_json({"epistemic_status": "draft"})



class TestGateError(unittest.TestCase):
    def test_as_dict(self):
        e = GateError("x", "msg")
        self.assertEqual(e.as_dict(), {"ok": False, "error_code": "x", "error": "msg"})


if __name__ == "__main__":
    unittest.main()

class TestVersionedDisclaimer(unittest.TestCase):
    def test_sealed_package_contains_canonical_disclaimer_and_version(self):
        from cueliez.gates import DISCLAIMER, DISCLAIMER_VERSION
        out = seal_observation_package({"observations": [_valid_obs()]})
        self.assertEqual(out["disclaimer"], DISCLAIMER)
        self.assertEqual(out["disclaimer_version"], DISCLAIMER_VERSION)
        self.assertTrue(out["disclaimer_version"].startswith("v1-"))

    def test_disclaimer_version_hash_based_changes_with_text(self):
        import hashlib
        text = "different disclaimer text for observation-only use."
        v = "v1-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        from cueliez.gates import DISCLAIMER_VERSION
        self.assertNotEqual(v, DISCLAIMER_VERSION)
