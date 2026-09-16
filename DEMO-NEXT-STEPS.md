# Demo next steps

```bash
cd /Volumes/CORSAIR/Workspace/Projects/localle_reservation_intake_final
git switch checkpoint/live-e2e-2026-09-15
git pull --ff-only origin checkpoint/live-e2e-2026-09-15
./scripts/start-localle.sh
./scripts/import-localle-workflow.sh
```

In the Google Sheet `Config` tab, confirm `auto_send_enabled` is exactly `FALSE`. In n8n, open the imported **Localle — AI Reservation Intake v2.0 FINAL (SAFE DEFAULT)** workflow and activate it only for this controlled test.

Send a new email to the dedicated labelled intake mailbox:

```text
Subject: Localle demo reservation — Test Customer A3

Hello, my name is Test Customer A3. Please arrange a small automatic car.
Pickup: Kos Airport, 18 July at 10:00.
Return: Kos Airport, 23 July.
My phone is +30 690 000 0001.
```

Expected result: one `Requests` row for the Gmail thread with `READY`, customer name, phone, pickup/return dates, and `ECONOMY` vehicle category; one `Processed_Messages` row with `DRAFT_ONLY`; and a prepared safe reply visible in n8n/Sheets, with no email sent.

Recording sequence (2–3 minutes): show `Config` with AUTO SEND false; send the email; show the successful n8n execution through Ollama and **Merge + Validate + Decide**; show the `Requests` and `Processed_Messages` rows; show the prepared reply and the absence of a sent message. Before stopping, show AUTO SEND is still `FALSE` unless deliberately performing one separately controlled outbound test.
