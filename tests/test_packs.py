import unittest

from cueliez.gates import GateError, record_consent, seal_observation_package
from cueliez.packs import CuePack, get_pack, list_packs
from cueliez.packs.definitions import gov_pack, leg_pack, med_pack, thrp_pack


SAMPLE_TRANSCRIPT = [
    {"role": "interviewer", "text": "Where were you last night?"},
    {"role": "subject", "text": "I think maybe I was around the place, you know, doing stuff.", "response_latency_ms": 4200},
    {"role": "subject", "text": "I was at home. I did not go there, I swear honestly.", "response_latency_ms": 900},
    {"role": "subject", "text": "Maybe 9:00 pm or 10:30 pm, not sure exactly."},
]


class TestPackRegistry(unittest.TestCase):
    def test_list_and_get(self):
        packs = list_packs()
        ids = {p["id"] for p in packs}
        self.assertEqual(ids, {"gov", "leg", "med", "thrp"})
        for pid in ids:
            p = get_pack(pid)
            self.assertIsInstance(p, CuePack)
            self.assertEqual(p.id, pid)

    def test_get_case_insensitive(self):
        self.assertEqual(get_pack("GOV").id, "gov")
        self.assertEqual(get_pack("  leg  ").id, "leg")

    def test_unknown_pack(self):
        with self.assertRaises(KeyError):
            get_pack("nope")


class TestPackModesAndGates(unittest.TestCase):
    def test_mode_mapping(self):
        self.assertEqual(gov_pack().mode, "government")
        self.assertEqual(leg_pack().mode, "interrogation")
        self.assertEqual(med_pack().mode, "clinical")
        self.assertEqual(thrp_pack().mode, "therapy")

    def test_make_gate_state_does_not_bypass_consent(self):
        for fn in (gov_pack, leg_pack, med_pack, thrp_pack):
            p = fn()
            s = p.make_gate_state()
            self.assertEqual(s.mode, p.mode)
            self.assertFalse(s.consent)
            self.assertFalse(s.training_acknowledged)
            # sealing must still enforce gates
            with self.assertRaises(GateError):
                seal_observation_package({"observations": []}, s)

    def test_gov_requires_dual_control_metadata(self):
        info = gov_pack().info()
        self.assertTrue(info["gates"]["dual_control_required"])
        self.assertTrue(info["gates"]["consent_required"])
        self.assertTrue(info["gates"]["training_required"])

    def test_leg_med_thrp_gate_requirements(self):
        for p, dual in ((leg_pack(), False), (med_pack(), False), (thrp_pack(), False)):
            info = p.info()
            self.assertTrue(info["gates"]["consent_required"])
            self.assertTrue(info["gates"]["training_required"])
            self.assertEqual(info["gates"]["dual_control_required"], dual)


class TestPackRunnersAndPackages(unittest.TestCase):
    def test_build_package_gate_compatible(self):
        for fn in (gov_pack, leg_pack, med_pack, thrp_pack):
            p = fn()
            pkg = p.build_package(SAMPLE_TRANSCRIPT, session_id="s1")
            self.assertEqual(pkg["session_id"], "s1")
            self.assertEqual(pkg["annotations"]["cue_pack"], p.id)
            self.assertEqual(pkg["annotations"]["cue_pack_mode"], p.mode)
            self.assertIsInstance(pkg.get("cue_guidance"), list)
            self.assertTrue(pkg["cue_guidance"])
            sealed = seal_observation_package(pkg)
            self.assertEqual(sealed["epistemic_status"], "observed_indicator")
            self.assertIs(sealed["is_definitive_finding"], False)

    def test_seal_with_proper_consent_state(self):
        p = leg_pack()
        pkg = p.build_package(SAMPLE_TRANSCRIPT)
        s = p.make_gate_state()
        record_consent(s, attested_by="officer-1")
        s.training_acknowledged = True
        s.training_version = "v1"
        sealed = seal_observation_package(pkg, s)
        self.assertTrue(sealed["firewall"]["consent_rechecked"])

    def test_gov_seal_requires_dual_control(self):
        from cueliez.gates import record_dual_acknowledge
        p = gov_pack()
        pkg = p.build_package(SAMPLE_TRANSCRIPT)
        s = p.make_gate_state()
        record_consent(s, attested_by="officer-1")
        s.training_acknowledged = True
        s.training_version = "v1"
        with self.assertRaises(GateError) as ctx:
            seal_observation_package(pkg, s, high_priority_cue_ids=["c1"])
        self.assertEqual(ctx.exception.code, "dual_control_incomplete")
        record_dual_acknowledge(s, "c1", "a", "b")
        seal_observation_package(pkg, s, high_priority_cue_ids=["c1"])

    def test_runners_have_observers(self):
        self.assertGreater(len(gov_pack().runner().observers), 5)
        self.assertGreater(len(leg_pack().runner().observers), 5)
        self.assertGreater(len(med_pack().runner().observers), 5)
        self.assertGreater(len(thrp_pack().runner().observers), 5)
        # med/thrp are curated subsets
        self.assertLessEqual(len(med_pack().runner().observers), len(leg_pack().runner().observers))
        self.assertLessEqual(len(thrp_pack().runner().observers), len(leg_pack().runner().observers))

    def test_feature_observers_opt_in(self):
        p = leg_pack()
        base = len(p.runner().observers)
        with_features = len(p.runner(include_feature_observers=True).observers)
        self.assertGreater(with_features, base)

    def test_med_thrp_have_domain_addendum(self):
        self.assertTrue(med_pack().build_package(SAMPLE_TRANSCRIPT).get("domain_disclaimer_addendum"))
        self.assertTrue(thrp_pack().build_package(SAMPLE_TRANSCRIPT).get("domain_disclaimer_addendum"))
        self.assertIn("diagnos", med_pack().disclaimer_addendum.lower())
        self.assertIn("credibility", thrp_pack().disclaimer_addendum.lower())


class TestPackLanguageCompliance(unittest.TestCase):
    FORBIDDEN_CLAIMS = ("lie detector", "detects lies", "truth detector", "confirms lying", "subject is lying")

    def test_no_forbidden_claims_in_pack_text(self):
        import json
        for p in (gov_pack(), leg_pack(), med_pack(), thrp_pack()):
            info = p.info()
            # Exclude the standard base disclaimer (vetted separately); check pack-authored text.
            authored = {
                "id": info["id"], "name": info["name"], "mode": info["mode"],
                "description": info["description"], "cue_guidance": info["cue_guidance"],
                "domain_notes": info["domain_notes"], "disclaimer_addendum": info["disclaimer_addendum"],
            }
            blob = json.dumps(authored, ensure_ascii=False).lower()
            for bad in self.FORBIDDEN_CLAIMS:
                self.assertNotIn(bad, blob, f"{p.id} contains forbidden claim {bad!r}")

    def test_guidance_affirms_human_judgment(self):
        for p in (gov_pack(), leg_pack(), med_pack(), thrp_pack()):
            g = " ".join(p.cue_guidance).lower()
            self.assertIn("human", g)
            self.assertTrue(("judgment" in g) or ("review" in g) or ("human-led" in " ".join(p.domain_notes).lower()))

    def test_observations_have_no_forbidden_labels(self):
        from cueliez.observations.base import FORBIDDEN_LABELS
        for p in (gov_pack(), leg_pack(), med_pack(), thrp_pack()):
            pkg = p.build_package(SAMPLE_TRANSCRIPT)
            for o in pkg["observations"]:
                self.assertNotIn(str(o.get("label", "")).lower(), FORBIDDEN_LABELS)
                self.assertIn("confidence", o)
                self.assertIn("model_id", o["confidence"])


if __name__ == "__main__":
    unittest.main()
