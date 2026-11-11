import json
import re
import unittest
from pathlib import Path
from unittest import mock

import cueliez.ingest as ing
from cueliez.gates import SessionGateState, seal_observation_package, verify_package_hash
from cueliez.ingest import (
    INGEST_ERROR_CODES,
    IngestError,
    build_ingested_package,
    canonicalize_turn,
    load_transcript,
    normalize_transcript,
    normalize_transcript_with_report,
    validate_transcript_turns,
)

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "transcripts"
DOC = (ROOT / "docs" / "TRANSCRIPT_INGEST_CONTRACT.md").read_text(encoding="utf-8")
CODES_DOC = (ROOT / "docs" / "GATE_ERROR_CODES.md").read_text(encoding="utf-8")

S = {"role": "subject", "text": "I was home."}
I = {"role": "interviewer", "text": "Where were you?"}

MALFORMED = {
    "unrecognised_wrapper.json": "ingest_unrecognised_structure",
    "container_not_a_list.json": "ingest_unrecognised_structure",
    "scalar_root.json": "ingest_unrecognised_structure",
    "two_containers.json": "ingest_ambiguous_structure",
    "empty_list.json": "ingest_empty_transcript",
    "empty_container.json": "ingest_empty_transcript",
    "all_empty.json": "ingest_empty_transcript",
    "number_turn.json": "ingest_invalid_turn",
    "null_turn.json": "ingest_invalid_turn",
    "bad_text_type.json": "ingest_invalid_turn",
    "unmapped_role.json": "ingest_unattributed_turn",
    "missing_role.json": "ingest_unattributed_turn",
    "conflicting_roles.json": "ingest_ambiguous_turn",
    "conflicting_text.json": "ingest_ambiguous_turn",
    "invalid_json.json": "ingest_invalid_input",
}


def doc_list(name):
    m = re.search(rf"\*\*{name}:\*\*(.*)", DOC)
    assert m, name
    return re.findall(r"`([^`]+)`", m.group(1))


class TestUnrecognisedInputFailsLoudly(unittest.TestCase):
    def test_foo_bar_raises_not_empty(self):
        with self.assertRaises(IngestError) as c:
            normalize_transcript({"foo": "bar"})
        self.assertEqual(c.exception.code, "ingest_unrecognised_structure")
        self.assertIn("foo", str(c.exception))

    def test_every_malformed_fixture_has_its_code(self):
        self.assertEqual(set(MALFORMED), {p.name for p in (FIX / "malformed").glob("*.json")})
        for name, code in MALFORMED.items():
            for fn in (normalize_transcript, load_transcript, build_ingested_package):
                with self.subTest(fixture=name, fn=fn.__name__):
                    with self.assertRaises(IngestError) as c:
                        fn(FIX / "malformed" / name)
                    self.assertEqual(c.exception.code, code)
                    self.assertIsInstance(c.exception, ValueError)

    def test_none_and_non_sequence_roots(self):
        for bad in (None, 5, True, b"[]", {"turns": "abc"}, {"turns": None}):
            with self.subTest(bad=bad):
                with self.assertRaises(IngestError):
                    load_transcript(bad)

    def test_missing_file_and_bad_json_string(self):
        with self.assertRaises(IngestError) as c:
            load_transcript("/nonexistent/transcript.json")
        self.assertEqual(c.exception.code, "ingest_invalid_input")
        with self.assertRaises(IngestError) as c:
            load_transcript('{"turns": [')
        self.assertEqual(c.exception.code, "ingest_invalid_input")

    def test_no_unvalidated_fallback(self):
        with self.assertRaises(IngestError):
            load_transcript([5])
        with self.assertRaises(ValueError):
            load_transcript([5])

    def test_error_names_turn_and_label(self):
        with self.assertRaises(IngestError) as c:
            load_transcript([S, {"role": "zzz", "text": "hi"}])
        e = c.exception
        self.assertEqual(e.turn_index, 1)
        self.assertIn("turn[1]", str(e))
        self.assertIn("zzz", str(e))
        self.assertEqual(e.as_dict()["error_code"], "ingest_unattributed_turn")
        with self.assertRaises(IngestError) as c:
            load_transcript([S, {"text": "hi"}])
        self.assertIn("no speaker field", str(c.exception))

    def test_null_turn_never_reduces_turn_count(self):
        with self.assertRaises(IngestError) as c:
            build_ingested_package([S, None, S])
        self.assertEqual(c.exception.code, "ingest_invalid_turn")
        self.assertEqual(c.exception.turn_index, 1)

    def test_canonicalize_rejects_non_mapping(self):
        with self.assertRaises(IngestError):
            canonicalize_turn(5)
        self.assertEqual(canonicalize_turn("hello"), {"role": "subject", "text": "hello"})

    def test_error_codes_documented(self):
        self.assertEqual(set(doc_list("INGEST_ERROR_CODES")), set(INGEST_ERROR_CODES))
        for code in INGEST_ERROR_CODES:
            self.assertIn(f"`{code}`", CODES_DOC)


class TestNoSilentDrops(unittest.TestCase):
    def test_second_text_alias_not_lost_when_first_blank(self):
        t = load_transcript([{"role": "subject", "text": "", "utterance": "hello"}])
        self.assertEqual(t[0]["text"], "hello")

    def test_nested_and_unknown_keys_preserved(self):
        t = load_transcript([{"role": "subject", "text": "a", "entities": [{"x": 1}], "meta2": {"k": [1, 2]}}])
        self.assertEqual(t[0]["entities"], [{"x": 1}])
        self.assertEqual(t[0]["meta2"], {"k": [1, 2]})

    def test_words_kept_alongside_derived_text(self):
        t = load_transcript([{"role": "subject", "words": [{"word": "I", "start": 0.1}, {"word": "left"}]}])
        self.assertEqual(t[0]["text"], "I left")
        self.assertEqual(t[0]["words"][0]["start"], 0.1)

    def test_unused_alias_fields_preserved(self):
        t = load_transcript([{"role": "subject", "text": "same", "content": "same", "channel": "0"}])[0]
        self.assertEqual(t["content"], "same")
        self.assertEqual(t["channel"], "0")

    def test_colliding_unmapped_role_kept(self):
        t = load_transcript([{"role": "zzz", "speaker": "suspect", "text": "x"}])[0]
        self.assertEqual(t["role"], "subject")
        self.assertEqual(t[ing.UNMAPPED_KEY], {"role": "zzz"})

    def test_wrapper_extra_keys_reported(self):
        _, rep = normalize_transcript_with_report({"turns": [S], "meeting_id": "m1", "vendor": {"a": 1}})
        self.assertEqual(rep["ignored_wrapper_keys"], ["meeting_id", "vendor"])
        self.assertEqual(rep["container"], "turns")

    def test_turn_count_equals_input_or_rejected(self):
        t, rep = normalize_transcript_with_report([S, I, S])
        self.assertEqual((rep["input_turn_count"], rep["accepted_turn_count"], len(t)), (3, 3, 3))

    def test_order_preserved(self):
        texts = [f"t{i}" for i in range(6)]
        t = load_transcript([{"role": "subject" if i % 2 else "officer", "text": x} for i, x in enumerate(texts)])
        self.assertEqual([x["text"] for x in t], texts)


class TestEmptyTurnPolicy(unittest.TestCase):
    def setUp(self):
        self.src = [I, {"role": "subject", "text": "  "}, S]

    def test_default_policy_is_flag(self):
        self.assertEqual(ing.EMPTY_TEXT_POLICY, "flag")
        self.assertEqual(doc_list("EMPTY_TEXT_POLICY"), [ing.EMPTY_TEXT_POLICY])

    def test_flag_keeps_position_and_reports(self):
        t, rep = normalize_transcript_with_report(self.src)
        self.assertEqual(len(t), 3)
        self.assertEqual(t[1][ing.INGEST_FLAGS_KEY], ["empty_text"])
        self.assertNotIn(ing.INGEST_FLAGS_KEY, t[0])
        self.assertEqual(rep["flagged_turns"], [{"index": 1, "code": "empty_text"}])
        self.assertEqual((rep["input_turn_count"], rep["accepted_turn_count"]), (3, 3))

    def test_role_only_turn_flagged_under_flag(self):
        t = load_transcript([I, {"role": "subject"}, S])
        self.assertEqual(t[1]["text"], "")
        self.assertEqual(t[1][ing.INGEST_FLAGS_KEY], ["empty_text"])

    def test_reject_names_turn_index(self):
        for bad in ({"role": "subject"}, {"role": "subject", "text": ""}, {"role": "subject", "text": "  "}):
            with self.subTest(bad=bad):
                with self.assertRaises(IngestError) as c:
                    load_transcript([I, bad, S], empty_text_policy="reject")
                self.assertEqual(c.exception.code, "ingest_empty_turn")
                self.assertEqual(c.exception.turn_index, 1)
                self.assertIn("turn[1]", str(c.exception))

    def test_reject_still_keeps_silence_segment_with_timing(self):
        t, rep = normalize_transcript_with_report(
            json.loads((FIX / "vendor" / "silence_segment.json").read_text()), empty_text_policy="reject")
        self.assertEqual(rep["flagged_turns"], [{"index": 1, "code": "empty_text"}])
        self.assertEqual(t[1]["pause_duration_ms"], 3200)
        self.assertEqual(t[1]["start_ms"], 1000)

    def test_silence_segment_keeps_metadata_under_flag(self):
        t = load_transcript(FIX / "vendor" / "silence_segment.json")
        self.assertEqual(t[1]["pause_duration_ms"], 3200)
        self.assertEqual(t[1][ing.INGEST_FLAGS_KEY], ["empty_text"])

    def test_policy_is_a_one_line_switch(self):
        with mock.patch.object(ing, "EMPTY_TEXT_POLICY", "reject"):
            with self.assertRaises(IngestError):
                load_transcript(self.src)
        self.assertEqual(len(load_transcript(self.src)), 3)

    def test_unknown_policy_rejected(self):
        with self.assertRaises(ValueError):
            load_transcript([S], empty_text_policy="drop")

    def test_all_empty_rejected_under_both_policies(self):
        src = [{"role": "subject", "text": "", "start": 0}, {"role": "interviewer", "text": " ", "start": 1}]
        for pol in ("flag", "reject"):
            with self.subTest(policy=pol):
                with self.assertRaises(IngestError) as c:
                    load_transcript(src, empty_text_policy=pol)
                self.assertEqual(c.exception.code, "ingest_empty_transcript")

    def test_validate_transcript_turns_takes_policy(self):
        with self.assertRaises(IngestError):
            validate_transcript_turns([I, {"role": "subject"}], empty_text_policy="reject")
        self.assertEqual(len(validate_transcript_turns([I, {"role": "subject"}])), 2)

    def test_non_text_keys_documented_match_code(self):
        self.assertEqual(doc_list("NON_TEXT_CONTENT_KEYS"), list(ing.NON_TEXT_CONTENT_KEYS))


class TestIngestReportInPackage(unittest.TestCase):
    def _pkg(self):
        return build_ingested_package([I, {"role": "subject", "text": " "}, S])

    def test_report_in_source_artifact(self):
        a = self._pkg()["source_artifact"]
        self.assertEqual(a["turn_count"], 3)
        self.assertEqual(a["ingest_report"]["flagged_turns"], [{"index": 1, "code": "empty_text"}])
        self.assertEqual(set(a["ingest_report"]), set(doc_list("INGEST_REPORT_FIELDS")))

    def test_report_is_inside_package_hash(self):
        sealed = seal_observation_package(self._pkg(), SessionGateState(mode="generic"))
        self.assertTrue(verify_package_hash(sealed))
        sealed["source_artifact"]["ingest_report"]["flagged_turns"] = []
        self.assertFalse(verify_package_hash(sealed))

    def test_no_report_when_source_artifact_off(self):
        self.assertNotIn("source_artifact", build_ingested_package([I, S], include_source_artifact=False))

    def test_source_name_for_path(self):
        p = FIX / "vendor" / "wrapper_turns.json"
        self.assertEqual(build_ingested_package(p)["source_artifact"]["name"], str(p))


class TestVendorFixtures(unittest.TestCase):
    def test_every_claimed_wrapper_key_has_fixture(self):
        self.assertEqual(doc_list("WRAPPER_KEYS"), list(ing.WRAPPER_KEYS))
        for k in ing.WRAPPER_KEYS:
            with self.subTest(key=k):
                f = FIX / "vendor" / f"wrapper_{k}.json"
                self.assertTrue(f.exists())
                t, rep = normalize_transcript_with_report(f)
                self.assertEqual([x["role"] for x in t], ["interviewer", "subject"])
                self.assertEqual(rep["container"], k)
                self.assertEqual(rep["ignored_wrapper_keys"], ["meeting_ref"])
                self.assertEqual(t[1]["end"], 4.6)

    def test_root_list_fixture(self):
        t, rep = normalize_transcript_with_report(FIX / "vendor" / "wrapper_root_list.json")
        self.assertEqual((len(t), rep["container"]), (2, "root"))

    def test_every_role_alias_has_fixture_turn(self):
        self.assertEqual(doc_list("ROLE_KEYS"), list(ing.ROLE_KEYS))
        raw = json.loads((FIX / "vendor" / "role_aliases_interviewer.json").read_text())
        self.assertEqual({k for turn in raw for k in turn} - {"text"}, set(ing.ROLE_KEYS))
        t = load_transcript(FIX / "vendor" / "role_aliases_interviewer.json")
        self.assertEqual({x["role"] for x in t}, {"interviewer"})
        self.assertEqual(len(t), len(ing.ROLE_KEYS))

    def test_subject_role_labels(self):
        t = load_transcript(FIX / "vendor" / "role_aliases_subject.json")
        self.assertEqual({x["role"] for x in t}, {"subject"})

    def test_every_text_alias_has_fixture_turn(self):
        self.assertEqual(doc_list("TEXT_KEYS"), list(ing.TEXT_KEYS))
        self.assertEqual(doc_list("TOKEN_KEYS"), list(ing.TOKEN_KEYS))
        raw = json.loads((FIX / "vendor" / "text_aliases.json").read_text())
        self.assertEqual({k for turn in raw for k in turn} - {"role"}, set(ing.TEXT_KEYS) | set(ing.TOKEN_KEYS))
        t = load_transcript(FIX / "vendor" / "text_aliases.json")
        self.assertTrue(all(x["text"].strip() for x in t))
        self.assertEqual(t[-2]["text"], "I left early")
        self.assertEqual(t[-1]["text"], "I did not see it")

    def test_vendor_fixtures_run_through_default_runner(self):
        from cueliez.observations import default_runner
        for f in sorted((FIX / "vendor").glob("*.json")):
            with self.subTest(fixture=f.name):
                pkg = default_runner().build_package(load_transcript(f))
                self.assertIsInstance(pkg["observations"], list)


if __name__ == "__main__":
    unittest.main()
