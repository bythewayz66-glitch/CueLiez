#!/usr/bin/env python3
"""Check version consistency across project metadata (Phase 9.2)."""
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    if not m:
        print("VERSION_CHECK_FAILED: pyproject.toml version not found"); return 1
    pv = m.group(1)
    init = (ROOT / "src/cueliez/__init__.py").read_text(encoding="utf-8")
    m2 = re.search(r'__version__\s*=\s*"([^"]+)"', init)
    if not m2:
        print("VERSION_CHECK_FAILED: src/cueliez/__init__.py __version__ not found"); return 1
    iv = m2.group(1)
    if pv != iv:
        print(f"VERSION_CHECK_FAILED: pyproject={pv} __init__={iv}"); return 1
    print(f"VERSION_CHECK_OK {pv}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
