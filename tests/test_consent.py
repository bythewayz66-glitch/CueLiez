import unittest

from cueliez.gates import GateError, SessionGateState, seal_observation_package
from cueliez.consent import (
    ConsentAcknowledgement,
    apply_consent_to_gate_state,
    domain_supplement,
    general_consent_form,
    get_consent_bundle,
    render_consent_form,
    validate_acknowledgement,
)


class TestConsentForms(unittest.TestCase):
    def test_general_form_structure(self):
        f = general_consent_form()
        self.assertEqual(f.domain, "general")
        self.assertTrue(f.disclosures)
        ids = {d.id for d in f.disclosures}
        self.assertIn("g_not_detector", ids)
        self.assertIn("g_no_automated_decisions", ids)
        self.assertTrue(all(d.required for d in f.disclosures))

    def test_domain_supplements(self):
        modes = {"gov": "government", "leg": "interrogation", "med": "clinical", "thrp": "therapy"}
        for dom, mode in modes.items():
            f = domain_supplement(dom)
            self.assertEqual(f.domain, dom)
            self.assertEqual(f.mode, mode)
            self.assertTrue(f.disclosures)
            self.assertTrue(f.id.startswith("cueliez-consent-"))

    def test_unknown_domain(self):
        with self.assertRaises(KeyError):
            domain_supplement("nope")

    def test_bundle(self):
        b = get_consent_bundle("leg")
        self.assertEqual(len(b), 2)
        self.assertEqual(b[0].domain, "general")
        self.assertEqual(b[1].domain, "leg")

    def test_render_contains_key_disclosures(self):
        text = render_consent_form(general_consent_form())
        self.assertIn("Not a lie detector", text)
        low = text.lower()
        self.assertTrue(("not findings" in low) or ("not a finding" in low) or ("not verdicts" in low))
        self.assertIn("attested_by", low.replace(" ", "_") + low)
        self.assertIn("acknowledgement", low)


class TestConsentValidation(unittest.TestCase):
    def _ack(self, form, **kw):
        base = dict(
            form_id=form.id, form_version=form.version, attested_by="off1",
            acknowledged_disclosure_ids=[d.id for d in form.disclosures if d.required],
            questions_opportunity_confirmed=True, voluntariness_confirmed=True,
        )
        base.update(kw)
        return ConsentAcknowledgement(**base)

    def test_valid_general(self):
        f = general_consent_form()
        r = validate_acknowledgement(f, self._ack(f))
        self.assertTrue(r.valid, r.validation_notes)
        self.assertEqual(r.attested_by, "off1")
        self.assertEqual(r.form_id, f.id)

    def test_missing_disclosures(self):
        f = general_consent_form()
        ack = self._ack(f, acknowledged_disclosure_ids=[])
        r = validate_acknowledgement(f, ack)
        self.assertFalse(r.valid)
        self.assertTrue(any("missing_required_disclosures" in n for n in r.validation_notes))

    def test_missing_attester(self):
        f = general_consent_form()
        r = validate_acknowledgement(f, self._ack(f, attested_by="  "))
        self.assertFalse(r.valid)
        self.assertIn("missing_attested_by", r.validation_notes)

    def test_missing_confirmations(self):
        f = general_consent_form()
        r = validate_acknowledgement(f, self._ack(f, questions_opportunity_confirmed=False))
        self.assertFalse(r.valid)
        r = validate_acknowledgement(f, self._ack(f, voluntariness_confirmed=False))
        self.assertFalse(r.valid)

    def test_form_mismatch(self):
        f = general_consent_form()
        r = validate_acknowledgement(f, self._ack(f, form_id="wrong"))
        self.assertFalse(r.valid)
        self.assertIn("form_id_mismatch", r.validation_notes)


class TestConsentGateIntegration(unittest.TestCase):
    def test_apply_to_gate_state(self):
        f = domain_supplement("leg")
        ack = ConsentAcknowledgement(
            form_id=f.id, form_version=f.version, attested_by="off1", subject_id="s1",
            jurisdiction="x",
            acknowledged_disclosure_ids=[d.id for d in f.disclosures],
            questions_opportunity_confirmed=True, voluntariness_confirmed=True,
        )
        rec = validate_acknowledgement(f, ack)
        state = SessionGateState(mode="interrogation")
        apply_consent_to_gate_state(rec, state)
        self.assertTrue(state.consent)
        self.assertEqual(state.consent_attested_by, "off1")
        self.assertIsNotNone(state.consent_recorded_at)

    def test_invalid_record_blocked(self):
        f = general_consent_form()
        rec = validate_acknowledgement(f, ConsentAcknowledgement(form_id=f.id, form_version=f.version, attested_by=""))
        state = SessionGateState(mode="clinical")
        with self.assertRaises(GateError) as ctx:
            apply_consent_to_gate_state(rec, state)
        self.assertEqual(ctx.exception.code, "invalid_consent_record")
        self.assertFalse(state.consent)

    def test_enables_seal_after_training(self):
        f = domain_supplement("leg")
        ack = ConsentAcknowledgement(
            form_id=f.id, form_version=f.version, attested_by="off1",
            acknowledged_disclosure_ids=[d.id for d in f.disclosures],
            questions_opportunity_confirmed=True, voluntariness_confirmed=True,
        )
        state = SessionGateState(mode="interrogation")
        apply_consent_to_gate_state(validate_acknowledgement(f, ack), state)
        state.training_acknowledged = True
        state.training_version = "v1"
        pkg = seal_observation_package({"observations": []}, state)
        self.assertTrue(pkg["firewall"]["consent_rechecked"])


class TestConsentLanguage(unittest.TestCase):
    def test_no_unnegated_forbidden_claims_in_forms(self):
        # General form contains the negated disclaimer; supplements must not introduce forbidden claims.
        for dom in (None, "gov", "leg", "med", "thrp"):
            forms = get_consent_bundle(dom)
            all_text = []
            for f in forms:
                text = render_consent_form(f).lower()
                all_text.append(text)
                self.assertNotIn("is a lie detector", text)
                self.assertNotIn("detects lies", text)
                self.assertNotIn("confirms lying", text)
                self.assertNotIn("subject is lying", text)
            combined = "\n".join(all_text)
            if dom is None or dom == "general" or forms[0].domain == "general":
                self.assertIn("not a lie detector", combined)


if __name__ == "__main__":
    unittest.main()
