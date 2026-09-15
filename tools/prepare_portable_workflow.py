#!/usr/bin/env python3
"""Create a temporary, name-bound import copy for a fresh n8n credential store."""
from __future__ import annotations

import hashlib
import json
import sys
import argparse
from pathlib import Path

EXPECTED_SHA256 = "1cfeb66a04b222a9519575b8521edc1d115c017dc76748e126cce32a2a0636a6"
CANONICAL_NAMES = {
    "gmailOAuth2": "Localle — Gmail OAuth",
    "googleSheetsOAuth2Api": "Localle — Google Sheets OAuth",
    "ollamaApi": "Localle — Ollama Local",
}
EXPECTED_COUNTS = {"gmailOAuth2": 8, "googleSheetsOAuth2Api": 16, "ollamaApi": 3}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument(
        "--credential-name",
        action="append",
        default=[],
        metavar="TYPE=NAME",
        help="override one canonical credential name for a supported import",
    )
    args = parser.parse_args()
    source, output = map(Path, (args.source, args.output))
    names = dict(CANONICAL_NAMES)
    for value in args.credential_name:
        credential_type, separator, name = value.partition("=")
        if not separator or credential_type not in names or not name:
            raise SystemExit("credential override must be a supported TYPE=NAME pair")
        names[credential_type] = name
    if hashlib.sha256(source.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise SystemExit("approved workflow SHA mismatch")
    workflow = json.loads(source.read_text(encoding="utf-8"))
    counts = {kind: 0 for kind in EXPECTED_COUNTS}
    for node in workflow["nodes"]:
        credentials = node.get("credentials", {})
        for credential_type in list(credentials):
            if credential_type in CANONICAL_NAMES:
                credentials[credential_type] = names[credential_type]
                counts[credential_type] += 1
    if counts != EXPECTED_COUNTS:
        raise SystemExit("unexpected credential-binding shape")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS — portable workflow prepared with supported credential names")


if __name__ == "__main__":
    main()
