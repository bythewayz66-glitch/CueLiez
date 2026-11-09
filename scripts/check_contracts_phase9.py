#!/usr/bin/env python3
"""Expanded contract checks (Phase 9.2): gate codes, schema/disclaimer refs, export formats."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

REQUIRED_GATE_CODES = [
    "consent_required", "training_required", "dual_control_required", "sealed_package",
    "invalid_training_ack", "connector_config_missing", "connector_unavailable",
]
REQUIRED_SCHEMA_FIELDS = [
    "epistemic_status", "is_definitive_finding", "disclaimer", "package_hash", "sealed_at", "schema_version", "gate_state",
]
REQUIRED_EXPORT_FORMATS = ["json", "md", "html"]

def main() -> int:
    from cueliez.gates import compute_package_hash, seal_observation_package, SessionGateState
    from cueliez.export import export_sealed_package
    import tempfile

    # Gate/seal contract
    pkg = seal_observation_package({"observations": []}, SessionGateState(mode="generic"))
    missing = [f for f in REQUIRED_SCHEMA_FIELDS if f not in pkg]
    if missing:
        print("CONTRACT_FAILED: sealed package missing fields: " + ", ".join(missing)); return 1
    if pkg.get("epistemic_status") != "observed_indicator" or pkg.get("is_definitive_finding") is not False:
        print("CONTRACT_FAILED: epistemic fields not enforced"); return 1
    if compute_package_hash(pkg) != pkg.get("package_hash"):
        print("CONTRACT_FAILED: package hash mismatch"); return 1

    # Export contract
    with tempfile.TemporaryDirectory() as td:
        paths = export_sealed_package(pkg, td, formats=REQUIRED_EXPORT_FORMATS)
        for fmt in REQUIRED_EXPORT_FORMATS:
            if fmt not in paths or not Path(paths[fmt]).exists():
                print(f"CONTRACT_FAILED: export format missing: {fmt}"); return 1
        html = Path(paths["html"]).read_text(encoding="utf-8", errors="ignore").lower()
        if "observed indicators and cues only" not in html or "disclaimer" not in html:
            print("CONTRACT_FAILED: export framing/disclaimer missing"); return 1

    # Gate codes presence in source/docs (lightweight check)
    gates_src = (ROOT / "src/cueliez/gates.py").read_text(encoding="utf-8", errors="ignore")
    for code in ["consent_required", "training_required", "dual_control_required"]:
        if code not in gates_src:
            print(f"CONTRACT_FAILED: gate code not found in gates.py: {code}"); return 1

    print("CONTRACTS_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
