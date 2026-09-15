# Upgrade policy

Never use `n8n@latest`. This release pins n8n `1.117.3` and model `llama3.1:8b`.

Back up before an upgrade. Test a copied state in isolation, validate its DB, import/export the workflow with the proposed version, run regression and the controlled provider matrix, compare semantics, and retain a rollback backup. Never migrate the only authoritative database on an untested n8n version.
