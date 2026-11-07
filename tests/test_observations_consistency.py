import unittest

from cueliez.gates import seal_observation_package
from cueliez.observations.consistency import (
    ClaimConflictObserver,
    DetailDriftObserver,
    LocationReferenceDivergenceObserver,
    SelfReferenceShiftObserver,
    TimelineInconsistencyObserver,
)


class TestConsistency(unittest.TestCase):
    def test_claim_conflict(self):
        t = [
            {"role": "subject", "text": "I entered the store yesterday."},
            {"role": "subject", "text": "I did not enter the store yesterday."},
        ]
        obs = ClaimConflictObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "possible_statement_conflict" for o in obs))
        seal_observation_package({"observations": obs})

    def test_timeline_multiple_times(self):
        t = [
            {"role": "subject", "text": "I arrived at 9:00 pm."},
            {"role": "subject", "text": "Then at 10:30 pm I left."},
        ]
        obs = TimelineInconsistencyObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "multiple_time_references_present" for o in obs))
        seal_observation_package({"observations": obs})

    def test_detail_drift(self):
        t = [
            {"role": "subject", "text": "There were 3 people."},
            {"role": "subject", "text": "Later I saw 5 people and 8 cars."},
        ]
        obs = DetailDriftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "numeric_detail_drift_observed" for o in obs))
        seal_observation_package({"observations": obs})

    def test_location_divergence(self):
        t = [
            {"role": "subject", "text": "I was at Boston near the river."},
            {"role": "subject", "text": "Then I went to Chicago."},
        ]
        obs = LocationReferenceDivergenceObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "multiple_location_references_present" for o in obs))
        seal_observation_package({"observations": obs})

    def test_self_reference_shift(self):
        t = [
            {"role": "subject", "text": "I went there and I saw it myself with my own eyes."},
            {"role": "subject", "text": "I told my friend and I knew what I did."},
            {"role": "subject", "text": "We went and we handled it and our group decided."},
        ]
        obs = SelfReferenceShiftObserver().observe(t).to_dicts()
        # heuristic may or may not trigger depending on thresholds; must be safe
        seal_observation_package({"observations": obs})

    def test_empty_safe(self):
        for cls in (ClaimConflictObserver, TimelineInconsistencyObserver, DetailDriftObserver,
                    LocationReferenceDivergenceObserver, SelfReferenceShiftObserver):
            seal_observation_package({"observations": cls().observe([]).to_dicts()})


if __name__ == "__main__":
    unittest.main()
