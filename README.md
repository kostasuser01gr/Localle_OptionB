# Localle — AI Reservation Intake & Conversion System

**Option B — Reservation request automation**  
Release: **v2.0 FINAL / safe default**

This package implements the Localle take-home as a small reservation-intake system rather than a simple email parser.

## What it does

`Gmail → normalize → duplicate/recovery guard → AI structured extraction → deterministic validation/state merge → Google Sheets UPSERT → reply-plan generation → multilingual reply render → semantic verifier → deterministic reply guard → safe send gate → same-thread Gmail reply → audit / human review`

Core behavior:
- extracts customer name, dates, category and phone;
- preserves one Google Sheet row per **reservation request / Gmail thread**, not one row per email;
- follow-up messages update the same request;
- asks only for required missing data;
- never guesses ambiguous dates or conflicting identity data;
- replies in the detected/requested language;
- supports neutral total-cost framing when a competitor price is mentioned;
- never invents live availability, live price, confirmed booking, or vehicle assignment;
- routes ambiguity and unsafe states to `Human_Review`;
- protects against auto-reply loops, bounce messages, duplicate Gmail events, prompt-injection text, uncertain send outcomes and AI extraction failures.

## Safe default

The exported workflow is **inactive**, contains **no credentials**, and the live Google Sheet has `Config → auto_send_enabled = FALSE`.

Even after the workflow is activated in n8n, no customer reply is sent until that Config value is deliberately changed to `TRUE`. Missing/invalid config resolves to `false`.

## Files to use

- `n8n/Localle_Option_B_Reservation_Intake_FINAL.n8n.json` — primary production workflow export.
- `n8n/localle_reservation_intake_v1.n8n.json` — identical compatibility copy used by the test harness.
- `n8n/localle_reservation_logic_demo.n8n.json` — credential-free logic replay.
- `schemas/extraction.schema.json` — strict extraction contract.
- `prompts/` — extractor, reply renderer and independent reply-verifier policies.
- `src/` — executable Python reference implementation and transactional SQLite test harness.
- `tests/` — regression, parity, fuzz, sequence, concurrency, n8n contract and Sheet contract tests.
- `evidence/` — generated validation, stress and simulation evidence.
- `docs/` — architecture, runbook, demo and submission material.
- `MANIFEST.sha256` — integrity hashes generated after the final validation pass.

## Live Google Sheet

Spreadsheet ID: `1j1hSY__8sCy7Ic4qHPaya3tzUqwQscEzlnKBv7JfbNc`

Tabs:
`Requests`, `Processed_Messages`, `Human_Review`, `Audit`, `Metrics`, `Config`, `Test_Cases`, `Validation`.

## Rebuild + validate

Requirements: Python 3.11+ recommended, Node.js, and `jsonschema` for the schema test.

```bash
python -m pip install -r requirements-dev.txt
python tools/run_validation.py
```

`run_validation.py` regenerates the base n8n workflow, applies the hardening pass, compiles the Python code, runs all tests, runs probability/stress scenarios, validates embedded JavaScript, scans for secrets, reconciles the workflow source and writes a final SHA-256 manifest.

## Codex handoff

`CODEX_MASTER_PROMPT.md` is the hardened handoff prompt for the final external verification pass. It instructs Codex to independently rerun the full release gate, perform a second random-seed stress pass, prove test sensitivity with mutation smoke tests, and close the remaining real-n8n runtime/import/E2E gate when the environment provides a safe test runtime and credentials.

The current release gate includes **77 unit/contract tests**, **two independent random-seed stress/probability runs**, and **6/6 detected critical mutations**. Synthetic probability figures are not production metrics.

## Controlled n8n activation

1. Import `n8n/Localle_Option_B_Reservation_Intake_FINAL.n8n.json`.
2. Bind Gmail credentials to Gmail Trigger/Gmail action nodes.
3. Bind Google Sheets credentials to the Sheets nodes.
4. Bind OpenAI credentials to the three Chat Model nodes.
5. Confirm the spreadsheet ID and tabs.
6. Leave `Config!auto_send_enabled = FALSE`.
7. Activate the workflow and send test emails **from a separate test mailbox**.
8. Verify `Requests`, `Processed_Messages`, `Human_Review`, `Audit`, and `reply_preview`.
9. Verify a second message in the same Gmail thread updates the same request row.
10. Only after the controlled cases pass, set `Config!auto_send_enabled = TRUE`.

See `docs/runbook.md` for the detailed checklist.

## Important production boundary

The exercise provides no real availability/fleet API and no live quote source. This system therefore intentionally stops at `READY` / “check availability and prepare exact offer” instead of fabricating a booking result.

Google Sheets is appropriate for the take-home and low-volume operational view, but hard distributed exactly-once guarantees under truly simultaneous executions require a transactional store (for example Postgres or an n8n transactional data store). The Python reference implementation proves the intended transaction semantics with SQLite; the Sheet workflow uses a durable message-ID ledger and safe recovery behavior but is described honestly as **best-effort idempotent** under distributed concurrency.

## Validation truthfulness

The generated n8n JSON is deeply static-tested and its Code nodes are syntax-checked. This execution environment does **not** contain an n8n runtime, so an actual import/execution inside the target n8n version is an explicit final external gate rather than a fabricated PASS. No real customer email has been sent during development.
