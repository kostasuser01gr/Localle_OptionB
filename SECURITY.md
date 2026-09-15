# Security and privacy

- AI inference is local Ollama only (`llama3.1:8b`); no cloud fallback is configured.
- n8n and Ollama are designed to bind to localhost.
- OAuth credentials remain encrypted in local n8n state under a fresh company-local key. The release has no credential export, token, cookie, database, or model binary. Losing the local key can make encrypted credentials unusable; never delete or silently replace it after credentials exist.
- Gmail retains source/reply email; Sheets retains requests, audit, ledger, and review records; n8n may retain execution data. Configure organization-approved execution/log retention before activation.
- Backups preserve encrypted n8n state and must be access-controlled. Never add secrets to `.env`, source, or frontend-public variables.
