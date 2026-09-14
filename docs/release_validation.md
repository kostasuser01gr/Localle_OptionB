# Release validation — v2.0-final-safe-default-codex-audit

Final automated release gate: **PASS**.

## Executed checks

- Unit / contract tests: **79 PASS**
- Python ↔ JavaScript parity: **10,000 cases**
- Unit fuzz: **25,000 cases**
- Multi-turn conversation stress: **40,000 conversations / 88,000 assertions**
- Reply-safety stress: **30,000 cases**
- Decision stress: **100,000 cases**
- Synthetic probability simulation: **150,000 requests total**
- Independent second-seed parity/stress/probability run: **PASS** (10,000 parity + 40,000 conversations + 30,000 reply-safety + 100,000 decision stress + 150,000 probability cases)
- Mutation sensitivity: **6/6 critical mutations detected**
- n8n production graph: **48 nodes**
- Embedded JavaScript syntax checks: **11 Code nodes**
- Release graph audit: **PASS**
- Static secret scan: **PASS**
- Workflow source reconciliation: **PASS**
- Live Google Sheet contract snapshot: **PASS**

## Synthetic automation scenarios

- Smooth assumptions: **96.58%** automated / **3.42%** human review
- Base assumptions: **92.314%** automated / **7.686%** human review
- Adverse assumptions: **85.13%** automated / **14.87%** human review

These are synthetic workload assumptions, not observed Localle production metrics.

## Safety state

- Workflow ships inactive.
- `Config → auto_send_enabled` defaults to `FALSE`.
- Missing/invalid config fails closed to no send.
- No credentials are embedded.
- Gmail customer send has no blind retry after an uncertain send result.
- Replies require both semantic verification and deterministic multilingual safety validation.
- AI extraction failure is persisted and escalated rather than silently dropped.

## Runtime gate

The workflow imported successfully into isolated **n8n 1.117.3** on Node 22.23.2. The imported export has all 48 nodes, no credentials, and remains inactive. A loopback-only runtime on `127.0.0.1:5679` passed `/healthz`; no missing-node or workflow-compatibility error was logged.

The remaining live gate is Gmail/Google Sheets/OpenAI controlled credentials. The isolated n8n credential store contains zero credentials, so no live E2E was attempted and auto-send remained `FALSE`.

## Codex audit repair

- Discovery: the credential-free replay reported mismatched return dates for German, French and ambiguous-date scenarios.
- Cause: each fixture returned before replacing the inherited return date.
- Fix: construct the fixture, set its intended return date, then return it.
- Regression: `tests.test_demo_replay` locks all three intended date pairs; the full suite now has 79 passing tests.
- Mutation copies exclude `.git`, `.venv`, `.n8n-runtime` and ZIP artifacts, so local runtime setup cannot affect mutation-test isolation.

## Production boundary

The exercise provides no real availability, live pricing or fleet source. The workflow therefore does not claim availability, quote a live price, confirm a booking, or allocate a vehicle. Hard distributed exactly-once semantics should move transactional state from Google Sheets to a transactional store if the system is productionized at larger concurrency.
