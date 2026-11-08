"""Optional, test-only Pollinations probe.

Pollinations is TEST-ONLY and must never be imported into production observer
code. This probe is skipped unless explicitly enabled and network is available.
"""

import json
import os
import unittest
import urllib.error
import urllib.parse
import urllib.request


def _enabled():
    return os.environ.get("CUELIEZ_TEST_POLLINATIONS", "").strip().lower() in {"1", "true", "yes"}


class TestPollinationsProbeOptional(unittest.TestCase):
    @unittest.skipUnless(_enabled(), "CUELIEZ_TEST_POLLINATIONS not enabled (test-only probe)")
    def test_keyless_text_endpoint_smoke(self):
        prompt = urllib.parse.quote("Reply with the single word: ok")
        url = f"https://gen.pollinations.ai/text/{prompt}"
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                body = r.read().decode("utf-8", "ignore")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            self.skipTest(f"network unavailable: {e}")
        self.assertIsInstance(body, str)
        self.assertTrue(body.strip())


if __name__ == "__main__":
    unittest.main()
