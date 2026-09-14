# Architecture — Localle Reservation Intake v2.0

## Design objective

Turn unstructured multilingual booking emails into a reliable reservation-intake conversation while optimizing for two things simultaneously:

1. **Conversion speed:** acknowledge/clarify fast so another office does not win purely by replying first.
2. **Operational truth:** never invent customer facts, live availability, a live quote, a confirmed booking or a vehicle assignment.

The system deliberately separates interpretation from authority.

## Trust boundaries

### Untrusted
- Gmail sender/body/HTML/quoted content/signatures.
- Any instructions contained inside customer text.
- First-pass AI extraction.
- AI-rendered customer reply.

### Trusted only after validation
- Strict extraction JSON that passes the schema.
- Deterministic status decision.
- Approved reply plan.
- Reply that passes both semantic and deterministic safety verification.

## End-to-end flow

```text
Gmail Trigger (unread inbox)
  ↓
Normalize Inbound
  ├─ strip quoted history/signature noise
  ├─ ignore auto responders / bounces / bulk
  └─ preserve immutable message_id + thread_id
  ↓
Lookup Config → Apply Runtime Config
  └─ missing/invalid auto_send value = false
  ↓
Processed_Messages lookup
  ├─ already replied → no-op
  └─ prior uncertain/non-replied → recovery review
  ↓
Requests lookup by thread_id
  ↓
Strict AI extraction
  ├─ bounded retry
  └─ failure → Human_Review + ledger + Audit; no customer send
  ↓
Deterministic Merge / Validate / Decide
  ├─ merge follow-up into same request
  ├─ explicit correction support
  ├─ unresolved ambiguity persistence
  ├─ confidence / conflict / date checks
  └─ READY | NEEDS_INFO | HUMAN_REVIEW
  ↓
UPSERT Requests
  ↓
Render customer reply from approved reply_plan
  ↓
Independent semantic reply verifier
  ↓
Deterministic multilingual reply guard
  ↓
Persist Processed_Messages event before send attempt
  ↓
Send gate
  ├─ Config auto_send_enabled must be true
  ├─ business state must allow reply (or safe holding acknowledgement)
  └─ both safety gates must pass
  ↓
Gmail Reply operation on original message
  ├─ success → mark ledger reply_sent + Audit
  └─ uncertain/error → DO NOT blind retry → Human_Review
```

## Three identities

The data model intentionally separates:

- `message_id`: immutable Gmail event identity. Used for duplicate protection.
- `thread_id`: conversation identity. Used to find the existing request.
- `request_id`: business entity identity. Used by operations/human review.

This is why a follow-up email does not create a second reservation row.

## State machine

### `READY`
Required intake fields are present and no blocking ambiguity/conflict exists. This does **not** mean a car is available or booked. Next step is availability/quote checking.

### `NEEDS_INFO`
The system can safely identify exactly what is missing or ambiguous. Reply plan asks only for the missing required fields.

Examples: missing name, missing phone, missing category, ambiguous `03/04` date.

### `HUMAN_REVIEW`
Automation should not commit to an interpretation.

Examples: conflicting identity, return before pickup, multiple independent rental requests, low extraction confidence, unsafe generated reply, extraction failure, uncertain send result.

### `NO_CHANGE`
Non-customer event or already processed message. No reply.

## Follow-up merge semantics

Neutral values such as `transmission=unspecified` never erase known facts. A message explicitly classified as `correction` may change operational fields such as pickup time/date/location, phone or requested category. Customer identity changes are not auto-corrected and create a conflict for human review.

Unresolved ambiguity survives unrelated follow-ups. Example: if `03/04` was ambiguous and the customer later supplies only a phone number, the ambiguous date remains unresolved.

## Reply safety

The renderer is not allowed to decide business state. It receives an approved plan.

Then two independent gates run:

1. **Semantic verifier:** checks language, factual fidelity, forbidden commitments and allowed questions.
2. **Deterministic multilingual guard:** blocks exact live prices, confirmation language, vehicle assignment, internal status leakage, competitor attacks, empty/oversized/code-fenced replies.

A reply is sendable only if both accept it.

## Failure model

- Extraction AI failure: bounded retries, then persisted human review. No send.
- Reply renderer/verifier failure: fail closed at reply gate.
- Google/Gmail event duplicate: message ledger prevents ordinary duplicate processing.
- Gmail send transport uncertainty: never automatically retry because the original send may have succeeded.
- Auto responders/bounces: filtered before extraction to prevent loops.

## Concurrency boundary

The Python reference uses `SQLite BEGIN IMMEDIATE` and proves one-commit behavior under concurrent duplicate calls. The n8n + Google Sheets implementation has a message ledger and recovery gates, but Sheets alone is not a transactional compare-and-set datastore across distributed n8n executions. At the brief's 20–30 emails/day this is a pragmatic implementation; production hard exactly-once semantics should move the event/request state to Postgres or another transactional store while keeping Sheets as the operational view.
