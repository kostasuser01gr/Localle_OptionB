# Live E2E evidence — pending authorized controlled test

Status: **NOT YET EXECUTED — release blocker for GO.** Credential metadata is present locally, but OAuth validity, scopes, controlled-mailbox access, live Sheets access, and the Config-sheet value have not been proven. The n8n workflow remains inactive.

OAuth checkpoint: the native Gmail credential’s client family resolves to Google Cloud project `localle-option-b-e2e`, not Program Shift. The required redirect URI must be added to the matching Google Auth Platform OAuth Web client before controlled E2E; see `evidence/oauth-client-resolution.json`.

Use two approved company test mailboxes and a dedicated test label. Keep `Config!auto_send_enabled = FALSE` for cases 1–7. Record only case IDs, timestamps, row/thread IDs, result, and reviewer in authorized company storage.

| Case | Required proof |
| --- | --- |
| Complete English | One `Requests` row, correct fields/thread/message IDs, `READY`, no send |
| Missing name/phone | `NEEDS_INFO`; asks only for name and phone |
| Same-thread follow-up | Same request row/ID; revision increments and blanks fill |
| German | Correct extraction and German reply |
| Competitor mention | Neutral reply; no comparison claim |
| `03/04` ambiguity | Clarification/preserved ambiguity; no invented ISO date |
| Prompt injection | No prompt exposure; human-safe state |
| Controlled outbound | Temporarily enable for test mailbox only; prove one same-thread reply, then re-read Config as `FALSE` |

Do not activate customer auto-send until every case passes and an authorized owner signs off.
