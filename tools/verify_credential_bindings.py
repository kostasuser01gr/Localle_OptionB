#!/usr/bin/env python3
"""Read-only verification that a stored workflow resolves all Localle credentials."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

EXPECTED_COUNTS = {"gmailOAuth2": 8, "googleSheetsOAuth2Api": 16, "ollamaApi": 3}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--workflow-id", default="LOCALLEOPTB2026A")
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    conn = sqlite3.connect(Path(args.db))
    row = conn.execute("SELECT nodes FROM workflow_entity WHERE id=?", (args.workflow_id,)).fetchone()
    if not row:
        print(json.dumps({"result": "PENDING", "reason": "workflow_not_imported"}))
        raise SystemExit(0 if args.allow_pending else 2)
    nodes = json.loads(row[0])
    counts = {kind: 0 for kind in EXPECTED_COUNTS}
    unresolved = 0
    for node in nodes:
        for credential_type, reference in (node.get("credentials") or {}).items():
            if credential_type not in EXPECTED_COUNTS:
                continue
            counts[credential_type] += 1
            if not isinstance(reference, dict) or not reference.get("id"):
                unresolved += 1
                continue
            match = conn.execute(
                "SELECT 1 FROM credentials_entity WHERE id=? AND type=? AND name=?",
                (reference["id"], credential_type, reference.get("name", "")),
            ).fetchone()
            if not match:
                unresolved += 1
    result = "PASS" if counts == EXPECTED_COUNTS and unresolved == 0 else "FAIL"
    print(json.dumps({"result": result, "binding_counts": counts, "unresolved": unresolved}))
    if result != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
