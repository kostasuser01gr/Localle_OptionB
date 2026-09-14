# Business logic

## Customer journey objective

The first automated response is not a receipt. It should remove uncertainty and advance the customer toward a booking without overpromising.

The system therefore follows this order:

1. Understand the request.
2. Confirm only the facts actually understood.
3. Ask only for information that is necessary and missing.
4. If the intake is complete, explain the next step: availability + exact offer.
5. If the customer mentions a cheap competing offer, compare **final payable conditions**, not headline prices, and never accuse the competitor.
6. Escalate instead of guessing.

## Required intake fields

- customer name
- phone
- pickup date
- return date
- vehicle category

The exercise additionally benefits from pickup/return location, time, transmission, model wording, customer email and competitor-price signal, so these are preserved when available.

## Price objection

A competitor price mention is a conversion signal, not permission to invent a quote.

Allowed framing:
- compare final payable total;
- mention only verified exercise inclusions;
- avoid naming or attacking competitors;
- continue the reservation conversation.

Not allowed:
- claim the competitor is misleading or fraudulent;
- repeat a fabricated current price;
- guarantee that Meltemi is cheaper without a live comparable quote.

## Missing information

A good clarification email should not make the customer repeat everything.

Example:

- already known: 18–23 July, small automatic, Kos Airport 10:00
- missing: full name, phone
- reply asks **only** for full name and phone.

A second customer message updates the same request row and can transition `NEEDS_INFO → READY`.

## Ambiguity vs missing data

- **Missing but clear:** ask the customer → `NEEDS_INFO`.
- **Ambiguous but safely clarifiable:** ask one clarification → `NEEDS_INFO`.
- **Conflicting / risky interpretation:** human → `HUMAN_REVIEW`.

`03/04` with no locale is a clarification case. Two different customer identities in one conversation is a human-review case.

## What READY means

`READY` means the intake data is sufficient for the *next business step*. It never means:
- booking confirmed;
- availability confirmed;
- exact price confirmed;
- specific vehicle allocated.
