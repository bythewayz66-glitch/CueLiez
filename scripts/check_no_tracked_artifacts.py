#!/usr/bin/env python3
"""Fail if build/bytecode artifacts are tracked (Phase 9.2/9.9)."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD_PREFIXES = ("build/", "dist/")
BAD_NAMES = ("__pycache__", ".pyc", ".pyo")

def main() -> int:
    r = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print("ARTIFACT_CHECK_SKIPPED: not a git repo or git unavailable")
        return 0
    bad = []
    for line in r.stdout.splitlines():
        if line.startswith(BAD_PREFIXES) or any(n in line for n in BAD_NAMES):
            bad.append(line)
    if bad:
        print("ARTIFACT_CHECK_FAILED")
        for b in bad: print(b)
        return 1
    print("ARTIFACT_CHECK_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
