# Known limitations

- Google Sheets does not guarantee transactional exactly-once behavior; idempotency is best-effort under distributed concurrency. Use a transactional datastore at higher volume.
- No live fleet availability or pricing source exists. The system must not promise availability, quote verified price, confirm booking, assign a vehicle, or guarantee transmission.
- Windows tooling is structurally prepared but not live-tested here.
- Provider-backed Gmail and Sheets E2E requires authorized controlled tests and is not yet claimed complete.
- The mandatory 2–3 minute demo is prepared as a script and checklist but is not recorded or published until controlled E2E and privacy review pass.
