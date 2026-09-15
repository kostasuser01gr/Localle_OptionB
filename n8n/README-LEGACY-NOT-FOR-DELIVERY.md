# Legacy workflow sources — not for delivery

`Localle_Option_B_Reservation_Intake_FINAL.n8n.json` and `localle_reservation_intake_v1.n8n.json` in this repository are historical dual-provider development sources. They are not the Localle zero-cost production workflow and must not be imported, activated, or included in a company delivery.

The only production workflow is the approved local-Ollama artifact validated by `tools/verify_zero_cost_release.py` and assembled into the release ZIP by `tools/create_release_package.py`. It has 48 nodes, runs only `llama3.1:8b` through local Ollama, is inactive by default, and contains zero OpenAI executable nodes.
