import unittest

from cueliez.gates import seal_observation_package
from cueliez.observations.linguistic import (
    CertaintySwingObserver,
    DetailVaguenessObserver,
    HedgingObserver,
    MemoryQualifierObserver,
    MinimizationObserver,
    NegationDensityObserver,
    OverjustificationObserver,
    PassiveVoiceProxyObserver,
    PronounDistancingObserver,
)


def _seal(obs_list):
    return seal_observation_package({"observations": obs_list})


class TestLinguistic(unittest.TestCase):
    def test_hedging_detected(self):
        t = [{"role": "subject", "text": "I think maybe perhaps I was sort of around there, not sure."}]
        obs = HedgingObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "hedging_language_present" for o in obs))
        _seal(obs)

    def test_distancing_detected(self):
        t = [{"role": "subject", "text": "That guy took the car and someone left the item there."}]
        obs = PronounDistancingObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "distancing_language_present" for o in obs))
        _seal(obs)

    def test_negation_detected(self):
        t = [{"role": "subject", "text": "I did not do it. I swear, honestly, I never went there, absolutely not."}]
        obs = NegationDensityObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "denial_or_emphatic_negation_present" for o in obs))
        _seal(obs)

    def test_vagueness_detected(self):
        t = [{"role": "subject", "text": "We did some stuff and things happened somewhere later, you know, whatever."}]
        obs = DetailVaguenessObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "low_specificity_language_present" for o in obs))
        _seal(obs)

    def test_certainty_swing(self):
        t = [
            {"role": "subject", "text": "I definitely absolutely saw him there."},
            {"role": "subject", "text": "Maybe I think I might have seen someone."},
        ]
        obs = CertaintySwingObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "certainty_shift_across_turns" for o in obs))
        _seal(obs)

    def test_minimization(self):
        t = [{"role": "subject", "text": "It was just a little thing, only minor, barely anything, no big deal really."}]
        obs = MinimizationObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "minimizing_language_present" for o in obs))
        _seal(obs)

    def test_passive_voice_proxy(self):
        t = [{"role": "subject", "text": "The door was opened and the money was taken and mistakes were made by the situation."}]
        obs = PassiveVoiceProxyObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "agentless_or_passive_constructions_present" for o in obs))
        _seal(obs)

    def test_overjustification(self):
        t = [{"role": "subject", "text": "Let me explain what happened was the reason is because I had to go because there was a thing and I mean I mean it was complicated for many reasons and details."}]
        obs = OverjustificationObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "extended_justification_present" for o in obs))
        _seal(obs)

    def test_memory_qualifier(self):
        t = [{"role": "subject", "text": "If I remember correctly, from what I recall it was fuzzy."}]
        obs = MemoryQualifierObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "memory_qualification_present" for o in obs))
        _seal(obs)

    def test_ignores_interviewer(self):
        t = [{"role": "interviewer", "text": "Maybe you are not sure, I think you never did it?"}]
        for cls in (HedgingObserver, NegationDensityObserver, DetailVaguenessObserver):
            self.assertEqual(cls().observe(t).to_dicts(), [])

    def test_empty_safe(self):
        for cls in (HedgingObserver, PronounDistancingObserver, NegationDensityObserver, DetailVaguenessObserver,
                    CertaintySwingObserver, MinimizationObserver, PassiveVoiceProxyObserver, OverjustificationObserver,
                    MemoryQualifierObserver):
            _seal(cls().observe([]).to_dicts())

    def test_sprint2_single_turn_noise_precision(self):
        # Thin evidence should not produce cues (precision over recall).
        self.assertEqual(HedgingObserver().observe(
            [{"role": "subject", "text": "I think it was fine today."}]
        ).to_dicts(), [])
        self.assertEqual(PronounDistancingObserver().observe(
            [{"role": "subject", "text": "Someone told me about the meeting yesterday."}]
        ).to_dicts(), [])
        self.assertEqual(DetailVaguenessObserver().observe(
            [{"role": "subject", "text": "You know it was okay in the afternoon."}]
        ).to_dicts(), [])
        self.assertEqual(CertaintySwingObserver().observe(
            [{"role": "subject", "text": "I definitely saw it happen clearly."}]
        ).to_dicts(), [])
        self.assertEqual(MinimizationObserver().observe(
            [{"role": "subject", "text": "It was just a small issue."}]
        ).to_dicts(), [])
        self.assertEqual(OverjustificationObserver().observe(
            [{"role": "subject", "text": "Let me explain what happened with the car."}]
        ).to_dicts(), [])


if __name__ == "__main__":
    unittest.main()
