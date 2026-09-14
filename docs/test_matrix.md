# Test matrix

The authoritative machine-readable results are in `evidence/validation_summary.json`, `evidence/stress_results.json`, `evidence/simulation_results.json`, and the live Sheet `Validation` tab.

Coverage includes:

- email HTML/plain-text normalization;
- quoted-history and signature stripping;
- bounce/auto-reply/bulk filtering;
- required-field detection;
- phone plausibility;
- vehicle taxonomy normalization;
- ambiguous numeric dates;
- return-before-pickup;
- multiple independent requests;
- low-confidence extraction;
- prompt-injection content treated as data;
- neutral `unspecified` follow-ups;
- explicit correction semantics;
- language switching;
- unresolved ambiguity persistence;
- identity conflicts;
- same-thread revision updates;
- SQLite transactional duplicate concurrency;
- Python ↔ JavaScript parity;
- n8n graph/import-contract invariants;
- live Google Sheet column contract;
- semantic reply verification;
- deterministic EN/DE/FR/IT/ES/EL confirmation blocking;
- exact price/vehicle assignment/internal-state/competitor attack blocking;
- extraction failure fail-closed path;
- uncertain Gmail-send no-blind-retry path;
- static secret scanning;
- high-volume synthetic probability and invariant stress.

Synthetic probability simulations are capacity/reasoning tools, **not observed production performance statistics**.
- independent second random-seed parity/stress/probability replay;
- mutation sensitivity smoke tests for safe-default activation, entity matching key, ambiguous-date guard, Greek confirmation guard, numeric-price guard, and Gmail blind-retry prevention.

