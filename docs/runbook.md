# Runbook — import, test, activate, recover

## 1. Preflight

- Confirm the live Google Sheet exists and contains all eight tabs.
- Confirm `Config!auto_send_enabled` is `FALSE`.
- Import `n8n/localle_reservation_intake_v1.n8n.json`.
- The imported workflow must be inactive initially.

## 2. Bind credentials

Bind credentials manually; the export intentionally ships without them.

The workflow was import-verified against n8n 1.117.3. Bind only controlled test credentials before its first live execution.

- Gmail credential: Gmail Trigger and every Gmail action node.
- Google Sheets credential: every Google Sheets node.
- OpenAI credential: `Extraction Model`, `Reply Model`, `Reply Safety Model`.

Do not paste secrets into Code nodes, prompts or the spreadsheet.

## 3. Credential-free logic check

Import and run `n8n/localle_reservation_logic_demo.n8n.json`. It performs no external writes/sends. Use it to inspect the basic status transitions.

Also run locally:

```bash
.venv/bin/python tools/run_validation.py
```

Expected: all gates PASS except the explicitly documented external n8n runtime gate if it has not yet been executed.

## 4. Controlled mailbox test — auto-send OFF

Activate the production workflow while `Config!auto_send_enabled=FALSE`.

From a separate test mailbox, send:

1. English request missing name + phone.
2. Follow-up in the same thread with name + phone.
3. Complete German request.
4. Competitor-price request.
5. Ambiguous `03/04` request.
6. Multiple independent requests.
7. Prompt-injection text.

Check:
- correct `Requests` status;
- same thread updates same `request_id` and increments revision;
- `reply_preview` is generated but nothing is sent;
- `Processed_Messages` contains the immutable Gmail message id;
- unsafe/ambiguous cases appear in `Human_Review`;
- `Audit` records the path.

## 5. Enable controlled auto-send

Only after dry-run verification, set `Config!auto_send_enabled` to `TRUE`.

Repeat the first two test-email cases. Verify:
- customer receives reply in the same Gmail thread;
- first reply asks only missing fields;
- follow-up updates same request;
- no n8n attribution is appended;
- no live availability or exact price is claimed.

Then restore `FALSE` until final demo if desired.

## 6. Error drills

### AI extraction fails
Expected: bounded retries then `Human_Review`, Processed_Messages ledger entry, Audit entry, no customer reply.

### AI generates unsafe reply
Expected: semantic verifier or deterministic guard blocks send and opens human review.

### Gmail reply returns uncertain/error
Expected: `SEND_UNCERTAIN`; no automatic resend. A person checks the Gmail Sent folder/thread first.

### Duplicate Gmail delivery
Expected: no duplicate request and no duplicate reply.

### Auto responder
Expected: ignored before AI extraction.

## 7. Rollback

Immediate kill switch: `Config!auto_send_enabled = FALSE`.

The workflow may remain active to collect/analyse requests without sending, or be deactivated entirely.

## 8. Production upgrade path

For real deployment beyond the take-home:
- move request/event transactional state from Sheets to Postgres or another transactional data store;
- connect actual availability and live pricing APIs;
- add real category/model mapping from fleet data;
- add business-specific age/insurance/location rules;
- keep Google Sheets as an operational/reporting view if staff prefer it.
