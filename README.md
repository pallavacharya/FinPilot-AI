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

## Module Integration Status

| Module | Owner | Status | Backend Location | Details |
|---|---|---|---|---|
| **Sales Forecasting** | **G Yaswanth Sai** | **COMPLETE** | `backend/modules/forecasting/` | 17 Prophet models trained & backtested (RMSE 1,708, WAPE 70.4%). Fixed-seed precomputed bundle (`forecast_bundle.json`) with zero extra runtime dependencies. Full API (`/categories`, `/next-week`, `/predict`, `/chart`, `/summary`) & Next.js "Product forecast" tab integrated. |
| Fraud detection | Kritagy Kaushik | Awaiting deliverable | `backend/modules/fraud/__init__.py` | Stubbed with sample data; awaiting Isolation Forest + XGBoost classifier on Kaggle fraud dataset. |
| RAG / documents | Pallav Acharya | Awaiting deliverable | `backend/modules/documents/__init__.py` | Stubbed with sample data; awaiting document chunking, embeddings, ChromaDB, and Claude API retrieval. |
| AI agent | Akshi Yadav | Awaiting deliverable | `backend/modules/agent/__init__.py` | Stubbed with sample data; awaiting LangGraph decision loop, action tools, and human approval flow. |

See `TEAM_INTEGRATION_GUIDE.docx` for the full per-person instructions.

## Project layout
    backend/                   FastAPI app (app/main.py, app/auth_utils.py = JWT + RBAC, app/routers/*)
    backend/modules/           Module implementations:
      forecasting/             [DONE] Real Prophet bundle, runtime reader, and training/ folder
      fraud/                   [STUB] Fraud detection module
      documents/               [STUB] Document retrieval / RAG module
      agent/                   [STUB] LangGraph agent module
    frontend/                  Next.js pages router (pages/, components/, lib/api.js, styles/)
      components/              ProductForecastChart (SVG), ProductForecastTab
    docker-compose.yml, start.bat, stop.bat

## Status / Current State
- **Infra & Auth**: Login, JWT authentication, RBAC enforced server-side, Docker configurations, unified `start.bat` / `stop.bat`.
- **Sales Forecasting (Yaswanth)**: 100% finished, tested, and integrated end-to-end (backend API + frontend SVG chart, search, dropdowns, table, overview KPI & top 8 cards).
- **Pending Teammates**: Fraud detection, Document Q&A, and Agent activity remain cleanly stubbed with their defined contracts, ready to plug in as soon as Kaushik, Pallav, and Akshi provide their code.
- **No Database Yet**: In-memory state for dev sessions; demo users in `routers/auth.py`.
