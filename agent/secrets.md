# Secrets — pointers only

| Credential | Where it lives |
|---|---|
| Provider API key | `.env` as `LLM_API_KEY` (legacy `GLM_API_KEY` supported) |
| Firecrawl API key | `.env` as `FIRECRAWL_API_KEY` |
| Upstash REST URL | `.env` locally; SSM `/ledger/traffic/upstash-rest-url` in production |
| Upstash REST token | `.env` locally; SecureString SSM `/ledger/traffic/upstash-rest-token` in production |
| Traffic notification address | `.env` locally; SSM `/ledger/traffic/notify-email` in production |

`.env.example` contains names/placeholders only. Never write real values into
run artifacts, logs, source, or this knowledge base.
