import json
import urllib.request
import unittest

from cueliez.delivery.dashboard import LiveDashboardServer


class TestDashboard(unittest.TestCase):
    def test_start_stop_and_cues(self):
        with LiveDashboardServer(host="127.0.0.1", port=0) as srv:
            url = srv.url
            # GET /
            with urllib.request.urlopen(url) as r:
                html = r.read().decode("utf-8")
            self.assertIn("Officer-only view", html)
            self.assertIn("CueLiez", html)
            # POST cues
            data = json.dumps({"cues": [{"cue_id": "c1", "message": "hi", "priority": "high", "score": 0.5, "category": "linguistic", "turn_index": 1}]}).encode()
            req = urllib.request.Request(url + "cues", data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as r:
                resp = json.loads(r.read())
            self.assertTrue(resp["ok"])
            self.assertEqual(resp["count"], 1)
            # GET cues
            with urllib.request.urlopen(url + "cues") as r:
                got = json.loads(r.read())
            self.assertEqual(len(got["cues"]), 1)
            self.assertEqual(got["cues"][0]["cue_id"], "c1")
            srv.stop()

    def test_subject_not_shown_wording(self):
        with LiveDashboardServer(host="127.0.0.1", port=0) as srv:
            with urllib.request.urlopen(srv.url) as r:
                html = r.read().decode("utf-8")
            self.assertIn("subject is not shown", html.lower())


if __name__ == "__main__":
    unittest.main()