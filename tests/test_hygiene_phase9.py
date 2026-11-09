"""Phase 9 hygiene/anti-fake checks."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_fake_code_markers_in_src():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_no_fake_code.py")], cwd=str(ROOT), capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout + "\n" + r.stderr
    assert "FAKE_CODE_SCAN_OK" in r.stdout
