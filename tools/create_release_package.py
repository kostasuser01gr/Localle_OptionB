#!/usr/bin/env python3
"""Create a delivery-safe Localle ZIP from the approved immutable artifact."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPROVED = ROOT / ".localle-zero-cost-go-20260915_181951/localle-zero-cost-ollama.json"
EXPECTED = "1cfeb66a04b222a9519575b8521edc1d115c017dc76748e126cce32a2a0636a6"
DIST = ROOT / "dist"
ZIP = DIST / "Localle_Option_B_FULLY_VERIFIED_ZERO_COST_FINAL.zip"

TOP_LEVEL = [
    "README.md", "INSTALL.md", "COMPANY-QUICKSTART.md", "OPERATIONS.md", "TROUBLESHOOTING.md",
    "SECURITY.md", "BACKUP-RESTORE.md", "UPGRADE.md", "TEST-MATRIX.md", "LIVE-E2E-EVIDENCE.md",
    "DEMO-SCRIPT-2-3-MIN.md", "DEMO-CHECKLIST.md", "KNOWN-LIMITATIONS.md", "ZERO-COST-VERIFICATION.md",
    "GO-NO-GO.md", "RELEASE-MANIFEST.json",
]
DIRECTORIES = ["scripts"]
CONFIG_FILES = ["config/live_sheet_contract.json"]
TOOL_FILES = [
    "tools/verify_zero_cost_release.py", "tools/prepare_portable_workflow.py",
    "tools/verify_credential_bindings.py", "tools/local_ollama_acceptance.py",
    "tools/audit_n8n_runtime_compatibility.js",
]
EVIDENCE_FILES = [
    "evidence/local_ollama_acceptance.json", "evidence/production-artifact-history.json",
    "evidence/release-candidate-checkpoint.json", "evidence/encryption-key-exposure-classification.json",
    "evidence/fresh-company-handover-drill.json", "evidence/oauth-client-resolution.json",
    "evidence/credential-probe-classification.json",
]
EXCLUDED_PARTS = {".git", ".venv", ".n8n-runtime", "node_modules", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".sqlite", ".db"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_tree(source: Path, target: Path) -> None:
    for item in source.rglob("*"):
        if not item.is_file() or EXCLUDED_PARTS.intersection(item.relative_to(source).parts) or item.suffix in EXCLUDED_SUFFIXES:
            continue
        destination = target / item.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)


def ensure_safe_tree(stage: Path) -> None:
    forbidden = ("database.sqlite", "cookies", "node_modules")
    bad = []
    for item in stage.rglob("*"):
        relative = item.relative_to(stage)
        if EXCLUDED_PARTS.intersection(relative.parts) or item.suffix in EXCLUDED_SUFFIXES:
            bad.append(str(relative))
        if item.name.lower().startswith(".env") or any(token in item.name.lower() for token in forbidden):
            bad.append(str(relative))
    if bad:
        raise SystemExit("delivery-unsafe file(s): " + ", ".join(sorted(set(bad))))


def main() -> None:
    if sha256(APPROVED) != EXPECTED:
        raise SystemExit("approved deployment artifact SHA mismatch")
    DIST.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="localle-release-") as temporary:
        stage = Path(temporary) / "Localle_Option_B_FULLY_VERIFIED_ZERO_COST_FINAL"
        stage.mkdir()
        for name in TOP_LEVEL:
            shutil.copy2(ROOT / name, stage / name)
        for name in DIRECTORIES:
            copy_tree(ROOT / name, stage / name)
        for name in CONFIG_FILES:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        for name in TOOL_FILES:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        for name in EVIDENCE_FILES:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        production = stage / "n8n" / "Localle_Option_B_Reservation_Intake_FINAL.n8n.json"
        production.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["python3", "tools/prepare_portable_workflow.py", str(APPROVED), str(production)],
            cwd=ROOT,
            check=True,
        )
        manifest_path = stage / "RELEASE-MANIFEST.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["approved_workflow_sha256"] = EXPECTED
        manifest["workflow_sha256"] = sha256(production)
        manifest["workflow_format"] = "portable_name_bound_import"
        manifest["release_package"] = ZIP.name
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        ensure_safe_tree(stage)
        subprocess.run(["python3", "tools/verify_zero_cost_release.py", "--portable", "n8n/Localle_Option_B_Reservation_Intake_FINAL.n8n.json"], cwd=stage, check=True)
        for script in list((stage / "scripts").glob("*.sh")) + [stage / "scripts" / "localle-n8n"]:
            subprocess.run(["bash", "-n", str(script)], check=True)
        hashes = []
        for item in sorted(path for path in stage.rglob("*") if path.is_file() and path.name != "SHA256SUMS"):
            hashes.append(f"{sha256(item)}  {item.relative_to(stage)}")
        (stage / "SHA256SUMS").write_text("\n".join(hashes) + "\n")
        temporary_zip = Path(temporary) / ZIP.name
        with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in sorted(path for path in stage.rglob("*") if path.is_file()):
                archive.write(item, item.relative_to(stage.parent))
        shutil.copy2(temporary_zip, ZIP)
    ZIP.with_suffix(ZIP.suffix + ".sha256").write_text(f"{sha256(ZIP)}  {ZIP.name}\n")
    print(f"PASS {ZIP}")


if __name__ == "__main__":
    main()
