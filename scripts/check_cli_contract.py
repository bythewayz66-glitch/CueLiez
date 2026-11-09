#!/usr/bin/env python3
"""Basic CLI/doc-contract checks (Phase 9.2)."""
from __future__ import annotations
import subprocess, sys

REQUIRED_FLAGS = ["--verify-package", "--sign", "--push-endpoint", "--pull-endpoint", "--pull-id", "--no-seal", "--mode"]

def main() -> int:
    r = subprocess.run([sys.executable, "-m", "cueliez", "--help"], capture_output=True, text=True)
    if r.returncode != 0:
        print("CLI_CONTRACT_FAILED: --help failed"); return 1
    helptext = r.stdout + r.stderr
    missing = [f for f in REQUIRED_FLAGS if f not in helptext]
    if missing:
        print("CLI_CONTRACT_FAILED: missing flags: " + ", ".join(missing)); return 1
    print("CLI_CONTRACT_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
