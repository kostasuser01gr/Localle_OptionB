# Known limits / non-negotiable truth boundaries

1. **No live availability source is provided.** The automation cannot truthfully say a car is available.
2. **No live pricing source is provided.** The exercise's €35/day is a business-context fact, not a current quote. Exact live prices are blocked from auto-send.
3. **No fleet model/category source is provided.** Only explicit or verified configured mappings may normalize model names.
4. **n8n runtime is unavailable in this execution environment.** The JSON, expressions, graph invariants and JavaScript are statically tested; actual import/execution remains a controlled external gate.
5. **Google Sheets is not a distributed transaction database.** Message-ID ledger + recovery logic provides strong practical duplicate protection at the exercise volume, but hard exactly-once under simultaneous distributed workers needs a transactional store.
6. **Language quality remains model-dependent.** A second semantic verifier and deterministic guard reduce unsafe output, but business copy should still be spot-checked in the target languages before production.
7. **Business policies must be confirmed by the owner.** Insurance, airport delivery, second-driver and deposit claims are taken from the exercise brief and should not be generalized to another rental company without verification.
