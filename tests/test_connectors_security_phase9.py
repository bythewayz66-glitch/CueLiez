"""Phase 9 connector egress/SSRF hardening tests (observation artifacts only)."""
import os
import unittest
from unittest import mock

from cueliez.connectors import ConnectorError, validate_connector_url


class TestConnectorUrlValidation(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_allows_https_and_http_loopback_literal(self):
        os.environ.pop("CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK", None)
        self.assertEqual(validate_connector_url("https://example.com/x"), "https://example.com/x")
        self.assertEqual(validate_connector_url("http://127.0.0.1:8080/ingest"), "http://127.0.0.1:8080/ingest")
        self.assertEqual(validate_connector_url("http://[::1]/x"), "http://[::1]/x")

    def test_rejects_bad_scheme(self):
        with self.assertRaises(ConnectorError) as ctx:
            validate_connector_url("file:///etc/passwd")
        self.assertEqual(ctx.exception.code, "connector_url_rejected")
        with self.assertRaises(ConnectorError):
            validate_connector_url("ftp://example.com/x")

    def test_rejects_embedded_credentials(self):
        with self.assertRaises(ConnectorError) as ctx:
            validate_connector_url("https://user:pass@example.com/x")
        self.assertEqual(ctx.exception.code, "connector_url_rejected")

    def test_blocks_link_local_metadata_ip_by_default(self):
        os.environ.pop("CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK", None)
        with self.assertRaises(ConnectorError) as ctx:
            validate_connector_url("http://169.254.169.254/latest/meta-data/")
        self.assertEqual(ctx.exception.code, "connector_egress_blocked")
        self.assertIn("link_local", str(ctx.exception))

    def test_blocks_private_rfc1918_by_default(self):
        os.environ.pop("CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK", None)
        with self.assertRaises(ConnectorError) as ctx:
            validate_connector_url("http://10.0.0.5/api")
        self.assertEqual(ctx.exception.code, "connector_egress_blocked")
        self.assertIn("private_network", str(ctx.exception))

    def test_allows_private_rfc1918_when_explicitly_opted_in(self):
        os.environ["CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK"] = "1"
        self.assertEqual(validate_connector_url("http://10.0.0.5/api"), "http://10.0.0.5/api")
        self.assertEqual(validate_connector_url("http://192.168.1.20/api"), "http://192.168.1.20/api")

    def test_link_local_metadata_still_blocked_even_when_private_opt_in(self):
        os.environ["CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK"] = "1"
        with self.assertRaises(ConnectorError) as ctx:
            validate_connector_url("http://169.254.169.254/latest/meta-data/")
        self.assertEqual(ctx.exception.code, "connector_egress_blocked")

    def test_blocks_multicast_and_unspecified_literals(self):
        os.environ.pop("CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK", None)
        with self.assertRaises(ConnectorError):
            validate_connector_url("http://224.0.0.1/")
        with self.assertRaises(ConnectorError):
            validate_connector_url("http://0.0.0.0/")

    def test_hostname_resolving_to_private_blocked_by_default(self):
        os.environ.pop("CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK", None)
        fake = [(2, 1, 6, "", ("192.168.1.20", 0))]
        with mock.patch("cueliez.connectors.socket.getaddrinfo", return_value=fake):
            with self.assertRaises(ConnectorError) as ctx:
                validate_connector_url("https://internal.example.local/ingest")
        self.assertEqual(ctx.exception.code, "connector_egress_blocked")

    def test_hostname_resolving_to_loopback_allowed(self):
        os.environ.pop("CUELIEZ_CONNECTOR_ALLOW_PRIVATE_NETWORK", None)
        fake = [(2, 1, 6, "", ("127.0.0.1", 0))]
        with mock.patch("cueliez.connectors.socket.getaddrinfo", return_value=fake):
            self.assertEqual(validate_connector_url("http://localhost/ingest"), "http://localhost/ingest")

    def test_host_allowlist_blocks_unlisted_host(self):
        os.environ["CUELIEZ_CONNECTOR_HOST_ALLOWLIST"] = "approved.example.test"
        with mock.patch("cueliez.connectors.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 0))]):
            with self.assertRaises(ConnectorError) as ctx:
                validate_connector_url("https://other.example.test/ingest")
        self.assertEqual(ctx.exception.code, "connector_url_rejected")
        self.assertIn("HOST_ALLOWLIST", str(ctx.exception))

    def test_host_allowlist_permits_listed_host(self):
        os.environ["CUELIEZ_CONNECTOR_HOST_ALLOWLIST"] = "approved.example.test, 93.184.216.0/24"
        with mock.patch("cueliez.connectors.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 0))]):
            self.assertEqual(
                validate_connector_url("https://approved.example.test/ingest"),
                "https://approved.example.test/ingest",
            )

    def test_host_allowlist_permits_cidr(self):
        os.environ["CUELIEZ_CONNECTOR_HOST_ALLOWLIST"] = "93.184.216.0/24"
        with mock.patch("cueliez.connectors.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 0))]):
            self.assertEqual(validate_connector_url("https://example.test/ingest"), "https://example.test/ingest")


if __name__ == "__main__":
    unittest.main()
