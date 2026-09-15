# Test matrix

Deterministic regression covers duplicates, own messages, auto-replies, extraction/reply/safety failures, malformed output, prompt injection, conflicting follow-ups, Sheets/Gmail failures, uncertain sends, restart paths, multilingual safety, concurrency, parity, fuzzing, and mutation sensitivity.

The provider-backed controlled matrix—complete English, missing contact data, same-thread follow-up, German, competitor mention, ambiguous date, prompt injection, and one controlled send—is in `LIVE-E2E-EVIDENCE.md`. Never test against a customer.
