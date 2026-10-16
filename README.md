# FinPilot AI — Frontend + Backend Infrastructure

Next.js dashboard and chat UI, FastAPI API gateway, JWT auth with role-based access control, and Docker packaging.
This module connects the forecasting, fraud-detection, RAG and agent modules into one product.

```
Browser (Next.js, :3000)  --HTTP + JWT-->  FastAPI gateway (:8000)  -->  module routers
                                                                         forecast / fraud / documents / agent
```

## Quick start (Windows)
Requirements: Python 3.10+, Node.js 18+.

    start.bat        # sets everything up on first run, starts both servers, opens the browser
    stop.bat         # stops both servers

## Quick start (manual / macOS / Linux)

    # backend
    cd backend
    python -m venv venv
    venv\Scripts\activate            # Windows   (macOS/Linux: source venv/bin/activate)
    pip install -r requirements.txt
    python -m uvicorn app.main:app --reload --port 8000

    # frontend (second terminal)
    cd frontend
    npm install
    npm run dev

Open http://localhost:3000 — API docs at http://127.0.0.1:8000/docs

## Docker

    cp .env.example .env
    docker compose up --build

## Demo accounts
| Email | Password | Role | Can do |
|---|---|---|---|
| owner@aaravretail.com | demo1234 | owner | everything, incl. clearing flagged transactions |
| analyst@aaravretail.com | demo1234 | analyst | read + approve agent actions (cannot clear fraud flags) |

## Configuration (`.env`, see `.env.example`)
`JWT_SECRET`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`. Never commit a real `.env`.

## How the other modules plug in
Each module has ONE stub file in `backend/modules/` with the exact function name and return shape the dashboard expects.
Replace the body of the function(s) with the real model — do not rename functions or change the returned keys.

| Module | Owner | File to edit | Function(s) | Must return |
|---|---|---|---|---|
| Sales forecasting | G Yaswanth Sai | `backend/modules/forecasting/__init__.py` | `get_forecast(horizon_days)` | `horizon_days, mape, rmse, actual[], forecast[], next_30d_total_inr` |
| Fraud detection | Kritagy Kaushik | `backend/modules/fraud/__init__.py` | `get_flagged_transactions()` | `total_scanned, transactions[{id, amount, customer, risk_score, status}]` |
| RAG / documents | Pallav Acharya | `backend/modules/documents/__init__.py` | `index_document(filename, content)`, `ask(question)` | `ask` -> `{answer, sources[]}` |
| AI agent | Akshi Yadav | `backend/modules/agent/__init__.py` | `get_actions()`, `approve_action(action_id, approved_by)` | actions `[{id, title, body, status}]` |

See `TEAM_INTEGRATION_GUIDE.docx` for the full per-person instructions.

## Project layout
    backend/    FastAPI app (app/main.py, app/auth_utils.py = JWT + RBAC, app/routers/*)
    backend/modules/   one folder per teammate module (forecasting, fraud, documents, agent)
    frontend/   Next.js pages router (pages/, lib/api.js = API client, styles/)
    docker-compose.yml, start.bat, stop.bat

## Status / known limitations
- Done: login, JWT, RBAC enforced server-side, all four routes, dashboard, chat UI, Docker files.
- Stubbed: each module in `backend/modules/` returns sample data until its real model is wired in.
- No database yet: fraud reviews and agent approvals are held in memory and reset when the backend restarts.
- Demo users are hardcoded with plain-text passwords in `routers/auth.py` — replace with a database and hashed passwords (or Supabase/Clerk) before any real deployment.
- Not yet deployed.
