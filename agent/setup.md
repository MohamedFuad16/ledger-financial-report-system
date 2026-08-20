# Setup

Project type: Python Flask API plus browser frontend.

## Prerequisites

- Python 3.11+
- Node.js 20+ once the React frontend is present

## Install and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm test -- --run && npm run build && cd ..
.venv/bin/python test_contract.py
.venv/bin/python server.py
```

The app is served at `http://localhost:5000`.

For client-only development, run `npm run dev` in `frontend/`; Vite proxies
`/api` to the Flask server on port 5000.

## Environment variables

`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`,
`LLM_REASONING_EFFORT`, and `LLM_TEMPERATURE`. Legacy `GLM_*` aliases remain
supported. Values live in `.env`; names/default examples live in `.env.example`.
