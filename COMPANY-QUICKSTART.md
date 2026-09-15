# Localle company quickstart

1. Install Node.js 20+ and Ollama from <https://ollama.com/download>.
2. Extract the release ZIP locally and run `./scripts/setup-localle.sh`, then `./scripts/start-localle.sh`.
3. Open <http://127.0.0.1:5678> and complete the n8n owner screen if shown. Setup generated a fresh protected local n8n encryption key; it is never included in this package. Keep a protected state backup because losing that key can make stored credentials unusable.
4. In **Credentials**, create exactly these three credentials: Gmail OAuth2 named `Localle — Gmail OAuth`; Google Sheets OAuth2 named `Localle — Google Sheets OAuth`; and local Ollama named `Localle — Ollama Local` pointing at `http://127.0.0.1:11434`. Complete Google’s browser authorization. Never add a cloud AI credential or copy a credential ID from another instance.
5. Run `./scripts/import-localle-workflow.sh`. It uses supported n8n import matching by credential name/type and resolves all 27 workflow bindings; do not bind nodes individually. The imported workflow remains inactive. Then run `./scripts/verify-localle.sh`; it reports only binding counts and unresolved-count, never credential data.
6. Confirm the eight Google Sheet tabs exist and `Config!auto_send_enabled` is `FALSE`.
7. Run `./scripts/verify-localle.sh` and complete `LIVE-E2E-EVIDENCE.md` using controlled company test mailboxes.

Requests are in `Requests`; exceptions are in `Human_Review`. The send switch is `Config!auto_send_enabled` and must stay `FALSE` until an authorized owner completes the controlled test.

Daily operations: `./scripts/status-localle.sh`, `./scripts/stop-localle.sh`, `./scripts/restart-localle.sh`, and `./scripts/backup-localle.sh`. If something fails, run verify and read `TROUBLESHOOTING.md`. Do not manually edit workflow JSON, the n8n database, or credential files.
