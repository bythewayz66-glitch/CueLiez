import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class _Handler(BaseHTTPRequestHandler):
    store = {}

    def log_message(self, format, *args):
        return

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            data = {}
        self.store["last_push"] = data
        resp = json.dumps({"ok": True, "received_product": data.get("product"), "has_hash": bool(data.get("package_hash"))}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)

    def do_GET(self):
        pkg = self.store.get("pull_package")
        if pkg is None:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error":"not found"}')
            return
        resp = json.dumps({"package": pkg}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)


def _run_cli(*args, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    if env_extra:
        env.update(env_extra)
    cmd = [sys.executable, "-m", "cueliez", *args]
    return subprocess.run(cmd, capture_output=True, timeout=60, env=env, cwd=str(ROOT))


class TestConnectorsCLI(unittest.TestCase):
    def setUp(self):
        _Handler.store = {}
        self.httpd = HTTPServer(("127.0.0.1", 0), _Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)

    def test_push_endpoint_exports_after_success(self):
        endpoint = f"http://127.0.0.1:{self.port}/ingest"
        transcript = ROOT / "docs/examples/owner_clean_interview.json"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            r = _run_cli(str(transcript), "--mode", "generic", "--push-endpoint", endpoint, "--out-dir", str(out), "--basename", "pkg")
            self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
            # export triggered after push
            self.assertTrue((out / "pkg.json").exists())
            self.assertTrue((out / "pkg.summary.md").exists())
            pushed = _Handler.store.get("last_push")
            self.assertIsInstance(pushed, dict)
            self.assertTrue(pushed.get("sealed"))
            self.assertIn("package_hash", pushed)
            # result reports push and exports
            out_obj = None
            for ln in r.stdout.decode().splitlines():
                try:
                    out_obj = json.loads(ln)
                    if isinstance(out_obj, dict) and out_obj.get("push"):
                        break
                except Exception:
                    pass
            self.assertIsNotNone(out_obj)
            self.assertEqual(out_obj["push"]["status"], 200)
            self.assertIn("exports", out_obj)

    def test_pull_exports(self):
        transcript = ROOT / "docs/examples/owner_clean_interview.json"
        # build a package to serve
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "src"
            r0 = _run_cli(str(transcript), "--mode", "generic", "--out-dir", str(out), "--basename", "p")
            self.assertEqual(r0.returncode, 0, r0.stderr.decode())
            _Handler.store["pull_package"] = json.loads((out / "p.json").read_text())
            pend = f"http://127.0.0.1:{self.port}/packages/{{id}}"
            out2 = Path(td) / "pulled"
            r = _run_cli("--pull-endpoint", pend, "--pull-id", "abc123", "--out-dir", str(out2), "--basename", "pulled")
            self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
            self.assertTrue((out2 / "pulled.json").exists())
            self.assertTrue((out2 / "pulled.summary.md").exists())

    def test_push_offline_graceful_error(self):
        transcript = ROOT / "docs/examples/owner_clean_interview.json"
        # use closed port
        r = _run_cli(str(transcript), "--mode", "generic", "--push-endpoint", "http://127.0.0.1:9/ingest", "--connector-retries", "0", "--connector-timeout", "1")
        self.assertNotEqual(r.returncode, 0)
        err = json.loads(r.stderr.decode())
        self.assertFalse(err.get("ok"))
        self.assertEqual(err.get("error_code"), "connector_unavailable")
        self.assertIn("notice", err)


if __name__ == "__main__":
    unittest.main()


    def test_push_uses_env_endpoint(self):
        endpoint = f"http://127.0.0.1:{self.port}/ingest"
        transcript = ROOT / "docs/examples/owner_clean_interview.json"
        r = _run_cli(str(transcript), "--mode", "generic", "--no-seal", env_extra={"CUELIEZ_PUSH_ENDPOINT": endpoint})
        self.assertEqual(r.returncode, 0, r.stderr.decode() + r.stdout.decode())
        self.assertIsInstance(_Handler.store.get("last_push"), dict)
