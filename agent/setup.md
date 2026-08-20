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

Hosted deployment variables also include `LEDGER_ADMIN_TOKEN` and
`CORS_ALLOWED_ORIGINS`. The production token is a SecureString at
`/ledger/backend/admin-token` in SSM Parameter Store, not a repository or Vercel
environment variable. The Vite client only receives the public
`VITE_API_BASE_URL`; the operator pastes the token into Settings, which stores it
in that browser's local storage.

## Production

- GitHub: `https://github.com/MohamedFuad16/ledger-financial-report-system`
- Public UI: `https://assignment.mohamedfuad.com` (Vercel canonical alias: `https://ledger-financial-report-system.vercel.app`)
- AWS API: `https://52-194-83-152.sslip.io`
- EC2: `i-01cd566c48321ea17`, `t3.medium`, `ap-northeast-1a`
- Management: AWS Systems Manager only; security group exposes HTTP/HTTPS but no SSH.
- Service checks: `systemctl status ledger-backend caddy` through SSM and `GET /api/health` externally.
