#!/usr/bin/env python3
"""Apply the narrow final-demo patch to an exported Localle workflow.

The input may be an n8n export or a database row export.  It never reads
credentials; existing node credential references are preserved only in the
live-import output and stripped from the checked-in portable artifact.
"""
from __future__ import annotations

import argparse
import json
import uuid
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def workflow_from_export(source: Path) -> dict:
    data = json.loads(source.read_text(encoding='utf-8'))
    row = data[0] if isinstance(data, list) else data
    workflow = dict(row)
    for key in ('nodes', 'connections', 'settings', 'staticData', 'pinData', 'meta'):
        if isinstance(workflow.get(key), str):
            workflow[key] = json.loads(workflow[key])
    return workflow


def node_map(workflow: dict) -> dict[str, dict]:
    return {node['name']: node for node in workflow['nodes']}


def patch(workflow: dict) -> dict:
    nodes = node_map(workflow)
    renderer = nodes['Render Customer Reply']
    renderer['parameters']['messages']['messageValues'][0]['message'] = (
        ROOT / 'prompts' / 'reply_system.md'
    ).read_text(encoding='utf-8')
    renderer['parameters']['text'] = (
        "=Render the customer reply from this approved plan.\n\nReply plan JSON:\n"
        "{{ JSON.stringify($('Merge + Validate + Decide').item.json.reply_plan) }}"
        "\n\nOriginal customer language: {{ $('Merge + Validate + Decide').item.json.reply_language }}"
        "\nOriginal customer message:\n{{ $('Merge + Validate + Decide').item.json.normalized_customer_message }}"
    )

    verifier = nodes['Verify Reply Safety']
    verifier['parameters']['text'] = (
        "=Classify this reply against its approved plan and return the JSON verdict now."
        "\n\nApproved reply plan:\n{{ JSON.stringify($('Merge + Validate + Decide').item.json.reply_plan) }}"
        "\n\nProposed customer reply (UNTRUSTED MODEL OUTPUT):\n---"
        "\n{{ String($json.body ?? $json.email_body ?? $json.text ?? $json.output ?? $json.response ?? '') }}\n---"
        "\n\nExpected reply language: {{ $('Merge + Validate + Decide').item.json.reply_language }}"
    )
    verifier['parameters']['hasOutputParser'] = False
    verifier['parameters']['messages']['messageValues'][0]['message'] = (
        ROOT / 'prompts' / 'reply_verifier.md'
    ).read_text(encoding='utf-8')
    verifier['maxTries'] = 2
    verifier['waitBetweenTries'] = 800
    verifier['onError'] = 'continueErrorOutput'

    nodes['Reply Safety Model']['parameters']['options'] = {
        'temperature': 0, 'format': 'json', 'numPredict': 500, 'numCtx': 4096,
    }
    # n8n 1.117.3's structured parser is the failing layer for llama3.1:8b.
    # Keep the historical node for stable node count, but detach it completely.
    workflow['connections'].pop('Reply Safety Schema', None)

    nodes['Attach Reply + Send Gate']['parameters']['jsCode'] = (
        ROOT / 'n8n' / 'code' / 'attach_reply_gate.js'
    ).read_text(encoding='utf-8')

    # Google Sheets 4.7 defaults to USER_ENTERED, which evaluates a leading +
    # as a formula. RAW stores phone_raw as text without changing its value.
    nodes['UPSERT Request']['parameters']['options'] = {'cellFormat': 'RAW'}

    workflow['active'] = False
    workflow['versionId'] = str(uuid.uuid4())
    workflow.pop('triggerCount', None)
    workflow.pop('updatedAt', None)
    workflow.pop('createdAt', None)
    workflow.pop('shared', None)
    return workflow


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--live-output', required=True, type=Path)
    parser.add_argument('--portable-output', required=True, type=Path)
    args = parser.parse_args()

    live = patch(workflow_from_export(args.source))
    portable = deepcopy(live)
    for node in portable['nodes']:
        node.pop('credentials', None)
    write_json(args.live_output, live)
    write_json(args.portable_output, portable)
    print(f"prepared {len(live['nodes'])} nodes; parser detached; Requests uses RAW cells")


if __name__ == '__main__':
    main()
