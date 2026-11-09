#!/usr/bin/env python3
"""Fail if src/ contains obvious fake-code/stub markers (Phase 9.1)."""
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
# Patterns that usually indicate fake/stub work in production source.
FORBIDDEN = [
    (re.compile(r"\bTODO\b|\bFIXME\b|\bXXX\b"), "todo/fixme marker"),
    (re.compile(r"NotImplementedError|raise\s+NotImplemented\b"), "NotImplemented"),
    (re.compile(r"implement later|not implemented yet", re.I), "deferred implementation text"),
]
# Allowlist: specific files/lines may be reviewed exceptions (keep minimal).
ALLOW = set()

def main() -> int:
    bad = []
    for p in SRC.rglob("*.py"):
        rel = p.relative_to(ROOT).as_posix()
        if "__pycache__" in rel:
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            key = f"{rel}:{i}"
            if key in ALLOW:
                continue
            for rx, label in FORBIDDEN:
                if rx.search(line):
                    bad.append(f"{rel}:{i}: {label}: {line.strip()}")
    if bad:
        print("FAKE_CODE_SCAN_FAILED")
        for b in bad:
            print(b)
        return 1
    print("FAKE_CODE_SCAN_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
