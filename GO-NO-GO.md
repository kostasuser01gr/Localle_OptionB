# GO / NO-GO

Current status: **NO-GO for customer production.**

Local checks passed: approved deployment integrity, pinned n8n `1.117.3`, authoritative database integrity, controlled inactive import/export round-trip, local Ollama API and `llama3.1:8b` presence, deterministic safety/regression evidence, and an isolated fresh-company-state import. The fresh-state drill generated its own protected key and used n8n-supported name/type matching to resolve all 27 bindings from three synthetic unconnected credential fixtures; it copied no development state or OAuth token.

Blockers:

1. An authorized operator must complete Gmail and Google Sheets OAuth for the three named company credentials, then complete the controlled Gmail → n8n → Ollama → Google Sheets matrix, including same-thread update and one controlled outbound reply, and prove by a fresh Sheets read that `Config!auto_send_enabled` is `FALSE`. See `LIVE-E2E-EVIDENCE.md`.
2. The final ZIP must be rebuilt, clean-extracted, secret-scanned, and committed/pushed only after the controlled provider evidence passes.
3. The development-key exposure is classed `D — EXTERNAL_UNKNOWN` because assistant/tool transcript retention cannot be independently proven. Do not rotate it ad hoc: the owner must approve a credential-store rotation/recovery procedure after E2E, because rotation can invalidate existing encrypted OAuth credentials. No secret value is recorded in this repository or release candidate. The company release uses a newly generated independent local key.
