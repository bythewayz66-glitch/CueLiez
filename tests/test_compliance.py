import unittest

from cueliez.gates import GateError, SessionGateState, seal_observation_package
from cueliez.compliance import (
    apply_training_to_gate_state,
    domain_disclaimer,
    domain_training,
    get_disclaimer_bundle,
    get_training_bundle,
    render_disclaimer,
    render_training_module,
    validate_training_ack,
)
from cueliez.compliance.training import TrainingAcknowledgement


class TestDisclaimers(unittest.TestCase):
    def test_general_and_domains(self):
        g = domain_disclaimer.__module__  # just ensure module loaded
        from cueliez.compliance.disclaimers import general_disclaimer
        gen = general_disclaimer()
        self.assertEqual(gen.domain, "general")
        self.assertIn("lie detector", gen.body.lower())  # negated in base disclaimer
        self.assertIn("not a lie detector", gen.body.lower())
        for dom in ("gov", "leg", "med", "thrp"):
            d = domain_disclaimer(dom)
            self.assertEqual(d.domain, dom)
            self.assertTrue(d.bullets)

    def test_bundle(self):
        b = get_disclaimer_bundle("med")
        self.assertEqual([x.domain for x in b], ["general", "med"])

    def test_render(self):
        text = render_disclaimer(domain_disclaimer("thrp"))
        self.assertIn("Therapy", text)
        self.assertIn("not a medical device", text.lower())

    def test_no_forbidden_claims(self):
        for dom in (None, "gov", "leg", "med", "thrp"):
            for d in get_disclaimer_bundle(dom):
                blob = (d.body + " " + " ".join(d.bullets)).lower()
                self.assertNotIn("detects lies", blob)
                self.assertNotIn("confirms lying", blob)
                self.assertNotIn("subject is lying", blob)


class TestTraining(unittest.TestCase):
    def test_domain_modules(self):
        modes = {"gov": "government", "leg": "interrogation", "med": "clinical", "thrp": "therapy"}
        for dom, mode in modes.items():
            m = domain_training(dom)
            self.assertEqual(m.domain, dom)
            self.assertEqual(m.mode, mode)
            self.assertTrue(m.required_topics)
            self.assertTrue(m.prohibited_uses_review)
            self.assertTrue(m.assessment_checks)

    def test_bundle(self):
        self.assertEqual(len(get_training_bundle()), 4)
        self.assertEqual(len(get_training_bundle("gov")), 1)

    def test_render(self):
        text = render_training_module(domain_training("leg"))
        self.assertIn("Legal", text)
        self.assertIn("Prohibited uses", text)
        low = text.lower()
        self.assertTrue(("no lie-detector framing" in low) or ("not a lie detector" in low) or ("lie detector" not in low.replace("no lie-detector framing", "")))

    def test_training_language(self):
        for dom in ("gov", "leg", "med", "thrp"):
            m = domain_training(dom)
            blob = " ".join(m.required_topics + m.prohibited_uses_review + m.operator_responsibilities).lower()
            self.assertNotIn("detects lies", blob)
            self.assertNotIn("confirms deception", blob)


class TestTrainingValidationAndGates(unittest.TestCase):
    def _ack(self, m, **kw):
        base = dict(module_id=m.id, module_version=m.version, operator_id="op1",
                    completed_topics=list(m.required_topics), assessment_passed=True)
        base.update(kw)
        return TrainingAcknowledgement(**base)

    def test_valid_ack(self):
        m = domain_training("gov")
        res = validate_training_ack(m, self._ack(m))
        self.assertTrue(res["valid"], res["notes"])

    def test_invalid_acks(self):
        m = domain_training("med")
        self.assertFalse(validate_training_ack(m, self._ack(m, operator_id=""))["valid"])
        self.assertFalse(validate_training_ack(m, self._ack(m, assessment_passed=False))["valid"])
        self.assertFalse(validate_training_ack(m, self._ack(m, module_id="x"))["valid"])
        self.assertFalse(validate_training_ack(m, self._ack(m, completed_topics=[]))["valid"])
        self.assertFalse(validate_training_ack(m, self._ack(m, completed_topics=["only one"]))["valid"])

    def test_apply_to_gate(self):
        m = domain_training("thrp")
        state = SessionGateState(mode="therapy")
        apply_training_to_gate_state(m, self._ack(m), state)
        self.assertTrue(state.training_acknowledged)
        self.assertEqual(state.training_version, m.version)

    def test_invalid_apply_blocked(self):
        m = domain_training("leg")
        state = SessionGateState(mode="interrogation")
        with self.assertRaises(GateError) as ctx:
            apply_training_to_gate_state(m, self._ack(m, assessment_passed=False), state)
        self.assertEqual(ctx.exception.code, "invalid_training_ack")
        self.assertFalse(state.training_acknowledged)

    def test_training_enables_seal_with_consent(self):
        from cueliez.gates import record_consent
        m = domain_training("med")
        state = SessionGateState(mode="clinical")
        record_consent(state, attested_by="clin1")
        apply_training_to_gate_state(m, self._ack(m), state)
        pkg = seal_observation_package({"observations": []}, state)
        self.assertTrue(pkg["firewall"]["training_rechecked"])


if __name__ == "__main__":
    unittest.main()
