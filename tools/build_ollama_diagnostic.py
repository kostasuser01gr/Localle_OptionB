#!/usr/bin/env python3
"""Build the isolated, credential-free local Ollama diagnostic workflow.

This diagnostic is intentionally separate from the production workflow.  It
exercises only localhost and never contains Gmail, Sheets, OpenAI, or a secret.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "n8n" / "Localle_Option_B_Ollama_Diagnostic.n8n.json"
MODEL = "llama3.1:8b"


def code(name: str, position: tuple[int, int], js: str) -> dict:
    return {
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": list(position),
        "parameters": {"jsCode": js},
    }


def main() -> None:
    workflow = {
        "name": "Localle — Ollama Zero-Cost Diagnostic (credential-free)",
        "id": "LOCALLEOLLAMADIAG2026",
        "active": False,
        "settings": {"executionOrder": "v1"},
        "nodes": [
            {
                "id": "manual-trigger",
                "name": "Manual Trigger",
                "type": "n8n-nodes-base.manualTrigger",
                "typeVersion": 1,
                "position": [-620, 0],
                "parameters": {},
            },
            code(
                "Build Local Probe",
                (-400, -100),
                """return [{json:{
  prompt:'Return JSON only: {"language":"en","customer_name":"Ada Test","phone":"+306900000000","pickup":{"date_text":"20 July 2027"},"return":{"date_text":"23 July 2027"},"vehicle":{"category":"ECONOMY"},"ambiguities":[],"confidence":0.95}',
  model:'llama3.1:8b'
}}];""",
            ),
            {
                "id": "ollama-http",
                "name": "Generate with Local Ollama",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.3,
                "position": [-160, -100],
                "parameters": {
                    "method": "POST",
                    "url": "http://127.0.0.1:11434/api/generate",
                    "sendBody": True,
                    "contentType": "raw",
                    "rawContentType": "application/json",
                    # Keep this diagnostic request literal so it also proves that
                    # raw JSON bodies are accepted by this pinned n8n version.
                    "body": json.dumps({
                        "model": MODEL,
                        "prompt": 'Return JSON only: {"language":"en","customer_name":"Ada Test","phone":"+306900000000","pickup":{"date_text":"20 July 2027"},"return":{"date_text":"23 July 2027"},"vehicle":{"category":"ECONOMY"},"ambiguities":[],"confidence":0.95}',
                        "format": "json",
                        "stream": False,
                        "options": {"temperature": 0, "num_predict": 240},
                    }),
                    "options": {"timeout": 90000},
                },
            },
            code(
                "Strictly Validate Local Response",
                (90, -100),
                """const raw=String($json.response??'');
let parsed;
try { parsed=JSON.parse(raw); } catch { throw new Error('OLLAMA_SCHEMA_REJECTED: malformed JSON'); }
const required=['language','customer_name','phone','pickup','return','vehicle','ambiguities','confidence'];
const missing=required.filter((key)=>parsed[key]===undefined||parsed[key]===null||parsed[key]==='');
if(missing.length || typeof parsed.pickup!=='object' || typeof parsed.return!=='object' || typeof parsed.vehicle!=='object' || !Array.isArray(parsed.ambiguities) || Number(parsed.confidence)<0 || Number(parsed.confidence)>1) {
  throw new Error('OLLAMA_SCHEMA_REJECTED: '+(missing.join(',')||'invalid field shape'));
}
return [{json:{diagnostic:'PASS',model:$json.model??'llama3.1:8b',provider:'ollama',contract:parsed,timeout_ms:90000}}];""",
            ),
            code(
                "Reject Malformed Response",
                (-160, 140),
                """const deliberatelyMalformed='{not valid JSON';
let rejected=false;
try { JSON.parse(deliberatelyMalformed); } catch { rejected=true; }
if (!rejected) throw new Error('Malformed-response guard unexpectedly accepted invalid JSON');
return [{json:{diagnostic:'PASS',malformed_response_rejected:true,provider:'ollama'}}];""",
            ),
        ],
        "connections": {
            "Manual Trigger": {"main": [[{"node": "Build Local Probe", "type": "main", "index": 0}, {"node": "Reject Malformed Response", "type": "main", "index": 0}]]},
            "Build Local Probe": {"main": [[{"node": "Generate with Local Ollama", "type": "main", "index": 0}]]},
            "Generate with Local Ollama": {"main": [[{"node": "Strictly Validate Local Response", "type": "main", "index": 0}]]},
        },
        "pinData": {},
        "meta": {"templateCredsSetupCompleted": True, "instanceId": ""},
        "tags": [],
    }
    OUT.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
    print(f"built {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
