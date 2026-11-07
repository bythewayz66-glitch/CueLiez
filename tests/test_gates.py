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


def _valid_obs(label="hesitation_marker_present", score=0.5, model_id="m/v1"):
    return {"label": label, "confidence": {"score": score, "model_id": model_id}, "evidence": {}}


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
            seal_observation_package({"observations": [{"label": "x"}]})
        self.assertEqual(ctx.exception.code, "missing_confidence")
        with self.assertRaises(GateError):
            seal_observation_package({"observations": [{"label": "x", "confidence": {"model_id": "m"}}]})

    def test_seal_rejects_bad_score(self):
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [_valid_obs(score=1.5)]})
        self.assertEqual(ctx.exception.code, "confidence_out_of_range")
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [_valid_obs(score=-0.1)]})
        self.assertEqual(ctx.exception.code, "confidence_out_of_range")
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [{"label": "x", "confidence": {"score": "no", "model_id": "m"}}]})
        self.assertEqual(ctx.exception.code, "invalid_confidence_score")

    def test_seal_rejects_missing_model_id(self):
        with self.assertRaises(GateError) as ctx:
            seal_observation_package({"observations": [{"label": "x", "confidence": {"score": 0.5, "model_id": ""}}]})
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


class TestGateError(unittest.TestCase):
    def test_as_dict(self):
        e = GateError("x", "msg")
        self.assertEqual(e.as_dict(), {"ok": False, "error_code": "x", "error": "msg"})


if __name__ == "__main__":
    unittest.main()
