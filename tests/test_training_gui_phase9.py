import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

from cueliez.training_gui import TrainingGUIServer


class TestTrainingGUI(unittest.TestCase):
    def test_gui_home_modules_quiz_sandbox_records(self):
        with tempfile.TemporaryDirectory() as td:
            with TrainingGUIServer(host="127.0.0.1", port=0, records_path=Path(td) / "rec.jsonl") as srv:
                # context manager not defined; use start/stop
                pass
        # manual
        with tempfile.TemporaryDirectory() as td:
            srv = TrainingGUIServer(host="127.0.0.1", port=0, records_path=Path(td) / "rec.jsonl")
            srv.start()
            try:
                base = srv.url
                with urllib.request.urlopen(base) as r:
                    html = r.read().decode("utf-8")
                self.assertIn("Training Portal", html)
                self.assertIn("observation/cue-only", html.lower())
                with urllib.request.urlopen(base + "api/modules") as r:
                    mods = json.loads(r.read())
                self.assertTrue(any(m["domain"] == "gov" for m in mods))
                with urllib.request.urlopen(base + "module/gov") as r:
                    self.assertIn("Government", r.read().decode("utf-8"))
                # quiz
                answers = {"c1": 1, "c2": 2, "c3": 1, "g1": 1}
                data = json.dumps({"operator_id": "op1", "actor": "trainer1", "answers": answers}).encode()
                req = urllib.request.Request(base + "api/quiz/gov/submit", data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req) as r:
                    res = json.loads(r.read())
                self.assertTrue(res["ok"])
                self.assertTrue(res["score"]["passed"])
                self.assertTrue(res["ack_valid"]["valid"])
                self.assertTrue(res["credential"]["credential_id"])
                cid = res["credential"]["credential_id"]
                with urllib.request.urlopen(base + "api/records/verify?id=" + cid) as r:
                    v = json.loads(r.read())
                self.assertTrue(v["ok"])
                # sandbox
                transcript = json.dumps({"transcript": '[{"role":"interviewer","text":"Where were you?"},{"role":"subject","text":"I think maybe around nine, I do not recall."}]'}).encode()
                req = urllib.request.Request(base + "api/sandbox/run", data=transcript, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req) as r:
                    sb = json.loads(r.read())
                self.assertTrue(sb["ok"])
                self.assertIn("observation/cue-only", sb["notice"].lower())
            finally:
                srv.stop()


if __name__ == "__main__":
    unittest.main()
