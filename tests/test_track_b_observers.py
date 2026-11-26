"""Track B (observers): new signal observers, feature-metadata path,
narrative wiring, default-on membership, and gated observers.

Owner decision 2026-11-25: all text + narrative observers on by default
in default_runner/full_runner/packs; feature observers included in the
lists but firing only on supplied feature metadata (+ consent when a
gate state is supplied); gated reversal observers off by default until
explicitly enabled (demographic inference behind its own separate gate).
"""
import json
import tempfile
import unittest
from pathlib import Path

from cueliez.gates import (
    SessionGateState,
    record_demographic_inference_consent,
    record_modality_consent,
    seal_observation_package,
)
from cueliez.observations import default_runner, full_runner
from cueliez.observations.behavioral import (
    FilledPauseClusterObserver,
    ResponseLatencyShiftObserver,
    SpeechRateTrendObserver,
)
from cueliez.observations.consistency import CrossTurnClaimRestatementObserver, PronounShiftObserver
from cueliez.observations.gated import (
    DemographicInferenceObserver,
    ExpressionFeatureObserver,
    FacePresenceConsistencyObserver,
    PitchVoiceQualityObserver,
    WearableFeatureObserver,
)
from cueliez.observations.linguistic import DetailDensityShiftObserver, HedgingClusterObserver
from cueliez.observations.narrative import (
    AgencyFramingObserver,
    SensoryDetailObserver,
    SpecificityShiftObserver,
    TemporalStructureObserver,
)
from cueliez.observations.prosody import PauseDensityShiftObserver
from cueliez.observations.visual import (
    BlinkRateTrendObserver,
    OffCameraGazeFrequencyObserver,
    RestlessnessShiftObserver,
)
from cueliez.packs import get_pack

NINE_FEATURE_METHODS = {
    "cueliez.observations.prosody.variability_shift/v1",
    "cueliez.observations.prosody.pause_pattern/v1",
    "cueliez.observations.prosody.voice_feature_shift/v1",
    "cueliez.observations.visual.gaze_pattern/v1",
    "cueliez.observations.visual.blink_rate/v1",
    "cueliez.observations.visual.motor_activity/v1",
    "cueliez.observations.physiological.heart_rate_shift/v1",
    "cueliez.observations.physiological.hrv_shift/v1",
    "cueliez.observations.physiological.electrodermal_shift/v1",
}


def _rich_feature_turns():
    """4 turns carrying every feature the 9 feature observers need."""
    base = {
        "pitch_variance": 10.0, "pause_total_ms": 200, "jitter": 0.01,
        "off_camera_gaze_share": 0.1, "blink_rate_per_min": 15,
        "gesture_count": 1, "head_movement_events": 0,
        "heart_rate_bpm": 72, "hrv_ms": 50, "eda": 1.0,
    }
    spike = {
        "pitch_variance": 80.0, "pause_total_ms": 5000, "jitter": 0.2,
        "off_camera_gaze_share": 0.95, "blink_rate_per_min": 60,
        "gesture_count": 20, "head_movement_events": 10,
        "heart_rate_bpm": 130, "hrv_ms": 10, "eda": 12.0,
    }
    turns = []
    for feats in (base, base, base, spike):
        turns.append({"role": "subject", "text": "answer here", **dict(feats)})
    return turns


class TestNewTextObservers(unittest.TestCase):
    def test_hedging_cluster(self):
        t = [{"role": "subject", "text": "Maybe I think I was sort of around there, I don't recall exactly what happened."}]
        obs = HedgingClusterObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "hedging_cluster_present" for o in obs), obs)
        self.assertGreaterEqual(len(obs[0]["evidence"]["hedge_types_present"]), 2)
        seal_observation_package({"observations": obs})

    def test_hedging_cluster_single_type_no_fire(self):
        t = [{"role": "subject", "text": "Maybe it was Tuesday, maybe Wednesday, maybe Thursday."}]
        self.assertEqual(HedgingClusterObserver().observe(t).to_dicts(), [])

    def test_detail_density_shift(self):
        # Constructed densities ~0.30, 0.26, 0.22, 0.18, 0.00 across 5 turns;
        # the sparse last turn is a robust outlier against the session.
        def _turn(n_numbers):
            words = ["walking", "home", "slowly", "yesterday", "evening", "after", "work",
                     "with", "friends", "talking", "about", "nothing", "much", "today"]
            nums = [str(10 * (k + 1)) for k in range(n_numbers)]
            return {"role": "subject", "text": " ".join(words + nums)}
        t = [_turn(6), _turn(5), _turn(4), _turn(3), _turn(0)]
        obs = DetailDensityShiftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "detail_density_shift_observed" for o in obs), obs)

    def test_claim_restatement(self):
        t = [
            {"role": "subject", "text": "I drove the red car to the bank on Main Street."},
            {"role": "subject", "text": "I took the red car down Main Street to the bank later."},
        ]
        obs = CrossTurnClaimRestatementObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "claim_restated_with_variation" for o in obs), obs)
        seal_observation_package({"observations": obs})

    def test_claim_restatement_verbatim_no_fire(self):
        t = [
            {"role": "subject", "text": "I drove the red car to the bank on Main Street."},
            {"role": "subject", "text": "I drove the red car to the bank on Main Street."},
        ]
        self.assertEqual(CrossTurnClaimRestatementObserver().observe(t).to_dicts(), [])

    def test_pronoun_shift(self):
        t = [
            {"role": "subject", "text": "I went home and I called my brother and I told him everything I knew."},
            {"role": "subject", "text": "I left early and I drove myself and I parked my car outside."},
            {"role": "subject", "text": "I waited and I watched and I wrote down what I saw myself."},
            {"role": "subject", "text": "He went to the store and they waited outside while she called him about the car."},
        ]
        obs = PronounShiftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "pronoun_pattern_shift_across_turns" for o in obs), obs)

    def test_new_text_observers_emit_nothing_on_empty(self):
        for cls in (HedgingClusterObserver, DetailDensityShiftObserver,
                    CrossTurnClaimRestatementObserver, PronounShiftObserver):
            self.assertEqual(cls().observe([]).to_dicts(), [], cls.__name__)


class TestNewAudioVisualObservers(unittest.TestCase):
    def test_latency_shift(self):
        t = [{"role": "subject", "text": "answer here", "response_latency_ms": ms}
             for ms in (800, 900, 850, 3000, 3200, 3100)]
        obs = ResponseLatencyShiftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "response_latency_shift_across_turns" for o in obs), obs)

    def test_speech_rate_trend(self):
        t = [{"role": "subject", "text": "one two three four five six seven eight nine ten",
              "duration_ms": d} for d in (3000, 3000, 3000, 6000, 6000, 6000)]
        obs = SpeechRateTrendObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "speech_rate_trend_shift_observed" for o in obs), obs)

    def test_filled_pause_cluster_single_turn(self):
        t = [{"role": "subject", "text": "um uh I was um there waiting"}]
        obs = FilledPauseClusterObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "filled_pause_cluster_observed" for o in obs), obs)

    def test_filled_pause_cluster_consecutive(self):
        t = [
            {"role": "subject", "text": "um I went uh there yesterday"},
            {"role": "subject", "text": "um we waited uh for a while"},
            {"role": "subject", "text": "I left at nine in the morning."},
        ]
        obs = FilledPauseClusterObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "filled_pause_cluster_observed" for o in obs), obs)

    def test_pause_density_shift(self):
        t = [{"role": "subject", "text": "answer", "pause_total_ms": ms}
             for ms in (200, 220, 210, 800, 900, 850)]
        obs = PauseDensityShiftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "pause_density_shift_observed" for o in obs), obs)

    def test_off_camera_gaze_frequency(self):
        t = [{"role": "subject", "text": "a", "off_camera_gaze_share": r}
             for r in (0.1, 0.2, 0.15, 0.7, 0.8, 0.6)]
        obs = OffCameraGazeFrequencyObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "off_camera_gaze_frequency_elevated" for o in obs), obs)
        for o in obs:
            self.assertNotIn("aversion", (o.get("cue") or "").lower())
            self.assertNotIn("aversion", json.dumps(o.get("evidence") or {}).lower())

    def test_off_camera_gaze_frequency_low_no_fire(self):
        t = [{"role": "subject", "text": "a", "off_camera_gaze_share": r}
             for r in (0.1, 0.2, 0.1, 0.15)]
        self.assertEqual(OffCameraGazeFrequencyObserver().observe(t).to_dicts(), [])

    def test_blink_rate_trend(self):
        t = [{"role": "subject", "text": "a", "blink_rate_per_min": r}
             for r in (15, 16, 15, 30, 32, 31)]
        obs = BlinkRateTrendObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "blink_rate_trend_shift_observed" for o in obs), obs)

    def test_restlessness_shift(self):
        t = [{"role": "subject", "text": "a", "gesture_count": g}
             for g in (1, 1, 2, 8, 9, 8)]
        obs = RestlessnessShiftObserver().observe(t).to_dicts()
        self.assertTrue(any(o["label"] == "movement_restlessness_shift_observed" for o in obs), obs)


class TestFeatureMetadataPath(unittest.TestCase):
    def test_nine_feature_observers_emit_with_metadata(self):
        obs = full_runner().build_package(_rich_feature_turns())["observations"]
        methods = {o["method"] for o in obs}
        missing = NINE_FEATURE_METHODS - methods
        self.assertFalse(missing, f"feature observers did not fire: {missing}; got {sorted(methods)}")
        seal_observation_package({"observations": obs})

    def test_nine_feature_observers_emit_nothing_without_metadata(self):
        t = [{"role": "subject", "text": "answer here"}] * 4
        obs = full_runner().build_package(t)["observations"]
        methods = {o["method"] for o in obs}
        self.assertFalse(methods & NINE_FEATURE_METHODS, methods)

    def test_nested_features_dict(self):
        # features.audio_features / .camera / .wearable nesting
        t = [
            {"role": "subject", "text": "a", "features": {"audio_features": {"pitch_variance": 10.0}}},
            {"role": "subject", "text": "a", "features": {"audio_features": {"pitch_variance": 11.0}}},
            {"role": "subject", "text": "a", "features": {"audio_features": {"pitch_variance": 10.0}}},
            {"role": "subject", "text": "a", "features": {"audio_features": {"pitch_variance": 80.0}}},
        ]
        obs = full_runner().build_package(t)["observations"]
        self.assertTrue(any(o["method"] == "cueliez.observations.prosody.variability_shift/v1" for o in obs), obs)
        t2 = [
            {"role": "subject", "text": "a", "features": {"wearable": {"heart_rate_bpm": 72}}},
            {"role": "subject", "text": "a", "features": {"wearable": {"heart_rate_bpm": 72}}},
            {"role": "subject", "text": "a", "features": {"wearable": {"heart_rate_bpm": 71}}},
            {"role": "subject", "text": "a", "features": {"wearable": {"heart_rate_bpm": 140}}},
        ]
        obs2 = full_runner().build_package(t2)["observations"]
        self.assertTrue(any(o["method"] == "cueliez.observations.physiological.heart_rate_shift/v1" for o in obs2), obs2)

    def test_features_list_argument(self):
        turns = [{"role": "subject", "text": "a"}] * 4
        feats = [{"pause_total_ms": 200}, {"pause_total_ms": 210},
                 {"pause_total_ms": 220}, {"pause_total_ms": 3000}]
        obs = full_runner().run(turns, features=feats)
        self.assertTrue(any(o["method"] == "cueliez.observations.prosody.pause_pattern/v1" for o in obs), obs)

    def test_features_json_file_path(self):
        turns = [{"role": "subject", "text": "a"}] * 4
        feats = [{"pause_total_ms": 200}, {"pause_total_ms": 210},
                 {"pause_total_ms": 220}, {"pause_total_ms": 3000}]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "features.json"
            p.write_text(json.dumps(feats), encoding="utf-8")
            obs = full_runner().run(turns, features_path=str(p))
        self.assertTrue(any(o["method"] == "cueliez.observations.prosody.pause_pattern/v1" for o in obs), obs)

    def test_wrapper_features(self):
        t = {"turns": [{"role": "subject", "text": "a"}] * 4,
             "features": [{"pause_total_ms": 200}, {"pause_total_ms": 210},
                          {"pause_total_ms": 220}, {"pause_total_ms": 3000}]}
        obs = full_runner().run(t)
        self.assertTrue(any(o["method"] == "cueliez.observations.prosody.pause_pattern/v1" for o in obs), obs)

    def test_feature_observers_gated_by_consent_when_gate_state_given(self):
        # No consent at all: feature observers must not run.
        s = SessionGateState(mode="interrogation")
        obs = full_runner().build_package(_rich_feature_turns(), gate_state=s)["observations"]
        self.assertFalse({o["method"] for o in obs} & NINE_FEATURE_METHODS, obs)
        # Audio consent only: prosody runs, visual/physio do not.
        record_modality_consent(s, "audio_features", attested_by="o", jurisdiction="jx", jurisdiction_approved=True)
        obs = full_runner().build_package(_rich_feature_turns(), gate_state=s)["observations"]
        methods = {o["method"] for o in obs}
        self.assertIn("cueliez.observations.prosody.pause_pattern/v1", methods)
        self.assertNotIn("cueliez.observations.visual.gaze_pattern/v1", methods)
        self.assertNotIn("cueliez.observations.physiological.heart_rate_shift/v1", methods)


class TestNarrativeWiring(unittest.TestCase):
    def test_narrative_in_both_runners(self):
        expected = {
            "cueliez.observations.narrative.temporal_structure/v1",
            "cueliez.observations.narrative.sensory_detail/v1",
            "cueliez.observations.narrative.agency_framing/v1",
            "cueliez.observations.narrative.specificity_shift/v1",
        }
        for r in (default_runner(), full_runner()):
            methods = {o.method_id for o in r.observers}
            self.assertTrue(expected <= methods, expected - methods)

    def test_narrative_fires_via_runner(self):
        # Extended account (>100 subject words) with almost no sensory
        # detail markers: the sensory-detail narrative observer fires.
        t = [
            {"role": "interviewer", "text": "Tell me what happened that evening, from the start."},
            {"role": "subject", "text": "I went to the store at six and I bought milk and bread and then I walked home and I called my brother and we talked for a while about the car and the red truck outside."},
            {"role": "interviewer", "text": "And then what did you do?"},
            {"role": "subject", "text": "Stuff happened and things went on for a while and then later something else happened and it was all kind of a blur really."},
            {"role": "interviewer", "text": "What did you do for the rest of the evening?"},
            {"role": "subject", "text": "I stayed on the couch for the rest of the evening and I watched the game until it ended and then I went to bed."},
            {"role": "interviewer", "text": "Anything else about that night?"},
            {"role": "subject", "text": "Not much else to add really, it was an ordinary evening and nothing unusual happened after that at all."},
        ]
        obs = default_runner().build_package(t)["observations"]
        self.assertTrue(any(o["method"] == "cueliez.observations.narrative.sensory_detail/v1" for o in obs), obs)

    def test_narrative_canonical_model_ids(self):
        for cls in (TemporalStructureObserver, SensoryDetailObserver,
                    AgencyFramingObserver, SpecificityShiftObserver):
            self.assertTrue(cls.method_id.startswith("cueliez.observations.narrative."),
                            cls.method_id)


class TestDefaultOn(unittest.TestCase):
    def test_runner_counts(self):
        self.assertEqual(len(default_runner().observers), 45)
        self.assertEqual(len(full_runner().observers), 51)

    def test_all_packs_include_all_text_narrative_and_feature_observers(self):
        text_methods = {o.method_id for o in default_runner().observers}
        for pid in ("gov", "leg", "med", "thrp"):
            methods = {o.method_id for o in get_pack(pid).runner().observers}
            self.assertTrue(text_methods <= methods, f"{pid} missing {sorted(text_methods - methods)}")
            self.assertTrue(NINE_FEATURE_METHODS <= methods, pid)

    def test_convergence_is_a_runner_observation(self):
        # Turn 0 fires two categories at once (linguistic hedging +
        # behavioral latency anomaly) -> one convergence observation.
        t = [
            {"role": "subject", "text": "I think maybe I was around there doing stuff.", "response_latency_ms": 5000},
            {"role": "subject", "text": "I did not do it, I swear honestly never.", "response_latency_ms": 900},
            {"role": "subject", "text": "Why would you ask that?", "response_latency_ms": 850},
        ]
        obs = default_runner().run(t)
        self.assertTrue(any(o["category"] == "multimodal" for o in obs), obs)
        # build_package must not duplicate the convergence observation.
        pkg = default_runner().build_package(t)["observations"]
        conv = [o for o in pkg if o["category"] == "multimodal"]
        self.assertEqual(len(conv), len({o["cue_id"] for o in conv}))


class TestGatedObservers(unittest.TestCase):
    def _face_turns(self):
        return [
            {"role": "subject", "text": "a", "features": {"face_presence": 1.0, "face_feature_stability": 0.9}},
            {"role": "subject", "text": "a", "features": {"face_presence": 1.0, "face_feature_stability": 0.9}},
            {"role": "subject", "text": "a", "features": {"face_presence": 0.0, "face_feature_stability": 0.9}},
            {"role": "subject", "text": "a", "features": {"face_presence": 1.0, "face_feature_stability": 0.3}},
        ]

    def test_face_presence_disabled_by_default(self):
        self.assertEqual(FacePresenceConsistencyObserver().observe(self._face_turns()).to_dicts(), [])
        obs = full_runner().build_package(self._face_turns())["observations"]
        self.assertFalse(any(o["method"] == "cueliez.observations.gated.face_presence_consistency/v1" for o in obs))

    def test_face_presence_fires_when_enabled(self):
        obs = FacePresenceConsistencyObserver().observe_with_context(self._face_turns(), enabled=True).to_dicts()
        self.assertTrue(any(o["label"] == "face_feature_consistency_variation_observed" for o in obs), obs)
        self.assertLessEqual(obs[0]["confidence"]["score"], 0.60)
        self.assertIn("not identification", json.dumps(obs[0]["evidence"]).lower())

    def test_face_presence_via_full_runner_opt_in(self):
        r = full_runner(enabled_gated_observers={"face_presence_consistency"})
        obs = r.build_package(self._face_turns())["observations"]
        self.assertTrue(any(o["method"] == "cueliez.observations.gated.face_presence_consistency/v1" for o in obs), obs)

    def test_face_presence_blocked_without_camera_consent(self):
        s = SessionGateState(mode="interrogation")
        res = FacePresenceConsistencyObserver().observe_with_context(
            self._face_turns(), enabled=True, gate_state=s)
        self.assertEqual(res.observations, [])

    def test_demographic_disabled_by_default(self):
        t = [{"role": "subject", "text": "a",
              "features": {"demographic_attributes": {"age_band": "30-39"}}}]
        self.assertEqual(DemographicInferenceObserver().observe(t).to_dicts(), [])

    def test_demographic_fires_only_with_separate_gate(self):
        t = [{"role": "subject", "text": "a",
              "features": {"demographic_attributes": {"age_band": "30-39"}}}]
        # Enabled but no gate state at all in the direct call: opt-in flag only.
        obs = DemographicInferenceObserver().observe_with_context(t, enabled=True).to_dicts()
        self.assertTrue(any(o["label"] == "supplied_demographic_attributes_noted" for o in obs), obs)
        self.assertLessEqual(obs[0]["confidence"]["score"], 0.45)
        self.assertIn("bias", json.dumps(obs[0]["evidence"]).lower())
        # Camera consent alone must NOT enable it.
        s = SessionGateState(mode="interrogation")
        record_modality_consent(s, "camera", attested_by="o", jurisdiction="jx", jurisdiction_approved=True)
        res = DemographicInferenceObserver().observe_with_context(t, enabled=True, gate_state=s)
        self.assertEqual(res.observations, [], "camera consent must not satisfy the separate demographic gate")
        # The separate record does enable it.
        record_demographic_inference_consent(
            s, attested_by="o", jurisdiction="jx", jurisdiction_approved=True,
            bias_warning_acknowledged=True)
        obs2 = DemographicInferenceObserver().observe_with_context(t, enabled=True, gate_state=s).to_dicts()
        self.assertTrue(any(o["label"] == "supplied_demographic_attributes_noted" for o in obs2), obs2)

    def test_expression_features_gated(self):
        t = [{"role": "subject", "text": "a",
              "features": {"expression_features": {"brow_raise": 0.7, "mouth_open": 0.2}}}]
        self.assertEqual(ExpressionFeatureObserver().observe(t).to_dicts(), [])
        obs = ExpressionFeatureObserver().observe_with_context(t, enabled=True).to_dicts()
        self.assertTrue(any(o["label"] == "supplied_expression_features_noted" for o in obs), obs)
        self.assertLessEqual(obs[0]["confidence"]["score"], 0.50)
        self.assertNotIn("emotion", (obs[0].get("cue") or "").lower())
        self.assertNotIn("emotion", obs[0]["label"])

    def test_pitch_voice_quality_gated(self):
        t = [{"role": "subject", "text": "a", "features": {"audio_features": {"f0_mean_hz": v}}}
             for v in (120.0, 121.0, 120.0, 180.0)]
        self.assertEqual(PitchVoiceQualityObserver().observe(t).to_dicts(), [])
        obs = PitchVoiceQualityObserver().observe_with_context(t, enabled=True).to_dicts()
        self.assertTrue(any(o["label"] == "pitch_voice_quality_shift_observed" for o in obs), obs)

    def test_wearable_gated(self):
        t = [{"role": "subject", "text": "a", "features": {"wearable": {"skin_temperature_c": v}}}
             for v in (36.5, 36.6, 36.5, 38.5)]
        self.assertEqual(WearableFeatureObserver().observe(t).to_dicts(), [])
        obs = WearableFeatureObserver().observe_with_context(t, enabled=True).to_dicts()
        self.assertTrue(any(o["label"] == "wearable_feature_shift_observed" for o in obs), obs)

    def test_face_recognition_observer_without_recognizer_emits_nothing(self):
        from cueliez.observations.gated import FaceRecognitionObserver
        t = [{"role": "subject", "text": "a", "face_image": "tests/fixtures/face/obama2.jpg"}]
        res = FaceRecognitionObserver().observe_with_context(t, enabled=True)
        self.assertEqual(res.observations, [])
        self.assertIn("face_recognizer_not_configured", res.notes)


if __name__ == "__main__":
    unittest.main()
