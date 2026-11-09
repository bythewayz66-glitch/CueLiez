"""Phase 9 export path/output hardening tests."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from cueliez.export import export_sealed_package, safe_export_basename


def _pkg():
    return {
        "product": "CueLiez",
        "epistemic_status": "observed_indicator",
        "is_definitive_finding": False,
        "disclaimer": "d",
        "observations": [],
    }


class TestExportPathHardening(unittest.TestCase):
    def test_safe_export_basename_strips_traversal(self):
        self.assertEqual(safe_export_basename("../../etc/passwd"), "passwd")
        self.assertEqual(safe_export_basename("../evil"), "evil")
        self.assertEqual(safe_export_basename(".."), "sealed_package")
        self.assertEqual(safe_export_basename(""), "sealed_package")
        self.assertEqual(safe_export_basename("case 1/report"), "report")

    def test_export_sealed_package_basename_cannot_escape_out_dir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "out"
            paths = export_sealed_package(_pkg(), root, basename="../../escape", formats=["json"])
            p = Path(paths["json"])
            self.assertTrue(p.exists())
            self.assertEqual(p.resolve().parent, root.resolve())
            self.assertNotIn("..", p.name)

    def test_export_files_have_restrictive_permissions_when_supported(self):
        if os.name == "nt":
            self.skipTest("POSIX permissions")
        with tempfile.TemporaryDirectory() as td:
            paths = export_sealed_package(_pkg(), td, basename="case1", formats=["json", "md", "html"])
            for path in paths.values():
                mode = os.stat(path).st_mode & 0o777
                self.assertEqual(mode, 0o600)


if __name__ == "__main__":
    unittest.main()
