# 2–3 minute demo script

## 0:00–0:20 — Problem + architecture

“This is not an email parser. Each Gmail thread becomes one reservation request. AI interprets the message, deterministic rules decide what is safe, and the first reply is designed to move the customer toward a booking without inventing availability or price.”

Show the n8n workflow quickly: Gmail → extraction → decision → Sheet → reply verification → Gmail reply.

## 0:20–0:55 — Missing-information case

Send/show:

> Hi, I need a small automatic car from 18 July until 23 July. We arrive at Kos airport around 10am.

Show `Requests`:
- dates/category/location extracted;
- name and phone blank;
- `NEEDS_INFO`;
- reply preview asks only name + phone.

## 0:55–1:20 — Conversation continuation

Reply in the same thread:

> My name is John Smith, mobile +44 7700 123456.

Show that the **same request row** updates, `revision` increases, and status becomes `READY` rather than creating a duplicate request.

## 1:20–1:45 — Conversion/business logic

Show French/English competitor-offer test. Explain that `competitor_price_mentioned` is captured, but the system frames final payable cost neutrally and does not fabricate a price or attack another company.

## 1:45–2:10 — Judgment / exception handling

Show `03/04` → `NEEDS_INFO`, and multiple independent rental requests → `HUMAN_REVIEW`.

Point to Human_Review queue: reason, next action, source message, suggested safe reply.

## 2:10–2:35 — Reliability/safety

Show `Processed_Messages` + Audit and explain:
- immutable message-id duplicate protection;
- auto responders filtered;
- extraction failure fails closed;
- reply passes a second semantic verifier plus deterministic multilingual guard;
- Gmail send uncertainty is never blindly retried.

## 2:35–2:50 — Close

“The exercise stops at intake/next-step readiness because there is no real availability or live pricing source in the brief. In production, I’d connect those APIs instead of allowing AI to invent them.”
