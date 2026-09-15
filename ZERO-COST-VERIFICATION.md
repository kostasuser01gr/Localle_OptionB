# Zero-cost AI verification

The approved production workflow SHA-256 is `1cfeb66a04b222a9519575b8521edc1d115c017dc76748e126cce32a2a0636a6`. Its activation note directs operators to local Ollama, not OpenAI; its node versions are compatible with pinned n8n `1.117.3`. The controlled import/export check found three local Ollama model bindings and zero OpenAI executable nodes. Setup pulls only `llama3.1:8b` and tests local JSON inference at `127.0.0.1:11434`; it contains no cloud API key or paid fallback.

Gmail and Sheets OAuth are business integrations, not AI inference, and still require organization authorization.
