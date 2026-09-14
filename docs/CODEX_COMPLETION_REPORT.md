# Codex completion report — 2026-09-14

## Final status

**NO-GO — controlled Gmail, Google Sheets and OpenAI credentials are unavailable.** The import and local n8n runtime gates now pass; live E2E remains correctly unclaimed.

## Environment

- macOS 26.3.1 (Darwin 25.3.0, arm64)
- Python 3.14.3 in a project-local `.venv`; `jsonschema` 4.26.0
- Node.js 22.23.2
- n8n 1.117.3, installed only in ignored `.n8n-runtime/` because the latest release requires Node 24 while this machine provides Node 22.23.2.

## Defect repaired

| Discovery | Cause | Fix | Regression evidence |
| --- | --- | --- | --- |
| Demo replay displayed inherited `23 July` return dates in scenarios whose pickup dates were August/September. | Three fixture functions returned before their return-date assignment. | Build each fixture, set its return field, then return it. | `tests.test_demo_replay` plus regenerated `evidence/demo_replay.json`; full suite: 78 PASS. |
| Local virtualenv, Git metadata, and isolated n8n state could enter a regenerated manifest. | The manifest walk did not exclude all workstation-local directories. | Excluded `.venv`, `.git`, and `.n8n-runtime` in the source manifest generator. | Final manifest is generated without those paths; the archive excludes them too. |
| Mutation smoke became slow after isolated n8n installation. | It copied ignored local runtime and virtualenv directories into every temporary mutation case. | Centralized ignored-artifact patterns and excluded `.git`, `.venv`, `.n8n-runtime`, evidence, and ZIPs. | `tests.test_mutation_smoke` plus a fresh 6/6 mutation run. |

## Verified results

- Unit / contract: 79 PASS.
- Python↔JavaScript parity: 10,000 cases PASS.
- Fuzz: 25,000 decisions PASS.
- Stress: 40,000 conversations / 88,000 assertions, 30,000 reply-safety cases, and 100,000 decision cases PASS.
- Probability: smooth/base/adverse models, 50,000 requests each (150,000 total); synthetic only.
- Independent second seed: PASS with the same parity/stress/probability scale.
- Mutation sensitivity: 6/6 detected.
- Graph audit: 48 nodes; one customer-send node; expressions resolve; every outbound path crosses semantic verification, deterministic reply guard, and runtime auto-send gate.
- Workflow remains inactive, credential-free, and `Europe/Athens`; config defaults auto-send to `FALSE`.
- n8n import: PASS — all 48 nodes imported and a CLI export preserved the exact node set, inactive state and zero serialized credentials.
- n8n runtime: PASS — loopback-only `127.0.0.1:5679/healthz` returned `{"status":"ok"}`; imported Gmail, Sheets retry/idempotency and auto-send settings were rechecked.
- Local Ollama API/list/health/logs and `claude-ultra -h` passed.

## External gates

- n8n import: PASS — n8n 1.117.3.
- Controlled credential-free runtime: PASS — loopback health check and imported workflow inspection.
- Gmail/Google Sheets/OpenAI E2E: BLOCKED — isolated n8n credential store contains zero credentials, and no safe credential source is available to this project.
- Live Sheet reconciliation: BLOCKED — local contract passed; no live connector access was available.

No customer email was sent, auto-send was not enabled, and the controlled runtime was stopped after verification.
