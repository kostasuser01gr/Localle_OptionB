# Operations

Use only the provided commands. `scripts/localle-n8n` is the authoritative launcher: it sets an explicit n8n user directory, localhost binding, and pinned runtime path so an empty n8n home cannot be created silently.

| Action | Command |
| --- | --- |
| Start | `./scripts/start-localle.sh` |
| Stop | `./scripts/stop-localle.sh` |
| Restart | `./scripts/restart-localle.sh` |
| Status | `./scripts/status-localle.sh` |
| Verify | `./scripts/verify-localle.sh` |
| Backup | `./scripts/backup-localle.sh` |
| Restore | `./scripts/restore-localle.sh --from ~/.localle/backups/TIMESTAMP` |

n8n binds to `127.0.0.1:5678`; Ollama must stay on `127.0.0.1:11434`. Before activation, review credentials, Sheets schema, and `Config!auto_send_enabled = FALSE`. After every controlled outbound test, re-read Config and prove it is `FALSE`.

For a fresh company state, create the three named credentials in `COMPANY-QUICKSTART.md` and run `./scripts/import-localle-workflow.sh`. The script uses supported n8n credential name/type matching during import, so the operator never binds the 27 workflow nodes one at a time.
