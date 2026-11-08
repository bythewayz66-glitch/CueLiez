import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCAN_PATHS = [
    ROOT / "docs/site/index.html",
    ROOT / "docs/site/ops.html",
    ROOT / "docs/site/review.html",
    ROOT / "README.md",
    ROOT / "docs/PITCH_26S.md",
    ROOT / "docs/demo/OPERATOR_DRY_RUN.md",
    ROOT / "docs/demo/PILOT_PREP.md",
    ROOT / "docs/demo/VALIDATION_NOTES.md",
    ROOT / "docs/ADMISSIBILITY_AND_DISCLOSURE.md",
]

# Positive verdict/deception claims that must not appear (observation/cue framing only).
# Keep targeted to avoid flagging refusal/safety language (e.g. "refuses automated...").
FORBIDDEN_CLAIM_PATTERNS = [
    r"\bsubject is lying\b",
    r"\bsubject is deceptive\b",
    r"\bproves?\s+(deception|lying|guilt)\b",
    r"\bconfirms?\s+(lying|deception|guilt)\b",
    r"\btruth detector\b",
    r"\bguilty verdict\b",
    r"\bnot guilty verdict\b",
    r"\bwe (?:can|will)?\s*detect (?:lies|deception)\b",
]

LIE_DETECTOR_NEGATION = re.compile(
    r"not a lie detector|is not a lie detector|is \*\*not\*\* a lie detector|"
    r"does not detect lies|it does not detect lies|do not detect lies|"
    r"not a polygraph|no\s+[\"“]?lie detector[\"”]?|never\s+.*lie detector",
    re.IGNORECASE,
)


class TestSiteLanguage(unittest.TestCase):
    def test_landing_emphasizes_not_lie_detector_and_observation(self):
        index = (ROOT / "docs/site/index.html").read_text(encoding="utf-8")
        self.assertIn("CueLiez", index)
        self.assertIn("Cue + Legal Interview Engine", index)
        self.assertRegex(index, re.compile(r"not a lie detector", re.IGNORECASE))
        low = index.lower()
        self.assertTrue(
            ("observation" in low) or ("observes" in low) or ("cues" in low),
            "landing page should emphasize observation/cues framing",
        )

    def test_shipped_site_docs_have_no_forbidden_verdict_claims(self):
        for path in SCAN_PATHS:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertTrue(path.exists(), f"expected shipped file missing: {path}")
                text = path.read_text(encoding="utf-8")
                low = text.lower()
                for pat in FORBIDDEN_CLAIM_PATTERNS:
                    self.assertIsNone(
                        re.search(pat, low),
                        f"forbidden claim pattern {pat!r} found in {path}",
                    )
                if "lie detector" in low or "detect lies" in low:
                    self.assertIsNotNone(
                        LIE_DETECTOR_NEGATION.search(text),
                        f"'lie detector/detect lies' appears without clear negation in {path}",
                    )
                    # Flag positive phrasing like "is a lie detector" / "use as a lie detector",
                    # but allow "Not a lie detector".
                    self.assertIsNone(
                        re.search(r"(?<!\bnot\s)\b(?:is|as|use as)\s+a\s+lie detector\b", low),
                        f"positive lie-detector phrasing found in {path}",
                    )
                    self.assertIsNone(
                        re.search(r"\bcan detect lies\b|\bwill detect lies\b", low),
                        f"positive lie-detection claim found in {path}",
                    )


if __name__ == "__main__":
    unittest.main()
