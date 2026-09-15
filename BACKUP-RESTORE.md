# Backup and restore

Run `./scripts/backup-localle.sh`. It uses SQLite backup and includes the workflow artifact, schema manifest, release manifest, and checksums—never a decrypted credential export.

To restore: stop Localle, run `./scripts/restore-localle.sh --from ~/.localle/backups/TIMESTAMP`, then start it. Restore validates checksums and SQLite integrity and saves the old database in `~/.localle/pre-restore`. A credential-bearing database must be restored with its matching protected n8n config/key; confirm the workflow is inactive before testing.
