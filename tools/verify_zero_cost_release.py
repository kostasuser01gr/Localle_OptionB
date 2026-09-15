#!/usr/bin/env python3
"""Verify the approved local-Ollama workflow without reading credential payloads."""
from __future__ import annotations

import hashlib
import json
import argparse
import sys
from pathlib import Path

EXPECTED_SHA256 = "1cfeb66a04b222a9519575b8521edc1d115c017dc76748e126cce32a2a0636a6"
CANONICAL_NAMES = {
    "gmailOAuth2": "Localle — Gmail OAuth",
    "googleSheetsOAuth2Api": "Localle — Google Sheets OAuth",
    "ollamaApi": "Localle — Ollama Local",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow_path", nargs="?", default="n8n/Localle_Option_B_Reservation_Intake_FINAL.n8n.json")
    parser.add_argument("--portable", action="store_true", help="verify the company name-bound import copy")
    args = parser.parse_args()
    workflow_path = Path(args.workflow_path)
    data = workflow_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if not args.portable and digest != EXPECTED_SHA256:
        raise SystemExit(f"workflow SHA mismatch: {digest}")
    workflow = json.loads(data)
    nodes = workflow.get("nodes", [])
    names = {node["name"] for node in nodes}
    if len(nodes) != 48 or len(names) != 48:
        raise SystemExit("expected exactly 48 uniquely named workflow nodes")
    if workflow.get("id") != "LOCALLEOPTB2026A" or workflow.get("active") is not False:
        raise SystemExit("workflow identity or inactive safety state is wrong")
    for source, kinds in workflow.get("connections", {}).items():
        if source not in names:
            raise SystemExit(f"unknown connection source: {source}")
        for branches in kinds.values():
            for branch in branches:
                for edge in branch:
                    if edge["node"] not in names:
                        raise SystemExit(f"unknown connection target: {edge['node']}")
    bindings = {"gmail": 0, "sheets": 0, "ollama": 0}
    for node in nodes:
        descriptor = f"{node.get('name', '')} {node.get('type', '')}".lower()
        if "openai" in descriptor:
            raise SystemExit(f"paid-AI executable node found: {node['name']}")
        for credential_type, reference in node.get("credentials", {}).items():
            lowered = credential_type.lower()
            if "gmail" in lowered:
                bindings["gmail"] += 1
            if "googlesheets" in lowered:
                bindings["sheets"] += 1
            if "ollama" in lowered:
                bindings["ollama"] += 1
            if args.portable and credential_type in CANONICAL_NAMES:
                if reference != CANONICAL_NAMES[credential_type]:
                    raise SystemExit(f"portable credential reference is not canonical: {node['name']}")
            if not args.portable and credential_type in CANONICAL_NAMES:
                if not isinstance(reference, dict) or not reference.get("id"):
                    raise SystemExit(f"approved workflow credential reference is invalid: {node['name']}")
        if node.get("type") == "@n8n/n8n-nodes-langchain.lmChatOllama":
            if node.get("parameters", {}).get("model") != "llama3.1:8b":
                raise SystemExit(f"unexpected model in {node['name']}")
    if bindings != {"gmail": 8, "sheets": 16, "ollama": 3}:
        raise SystemExit(f"unexpected credential binding counts: {bindings}")
    print(json.dumps({"result": "PASS", "sha256": digest, "portable": args.portable, "nodes": len(nodes), "active": False, "bindings": bindings, "paid_ai_nodes": 0}))


if __name__ == "__main__":
    main()
